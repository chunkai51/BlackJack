"""基于 LLM 的 Blackjack 庄家 Agent。

本模块将原本的命令行流程拆分为“工具”接口，
由大模型通过函数调用来驱动游戏，同时保持可聊天能力。

使用者需自行填写/注入 LLM 配置（环境变量优先），
运行时如果缺少配置会给出友好提示。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .game import Game

# 从本地 config.py 读取密钥/模型，如不存在则回退到环境变量
try:
    from config import API_KEY as CONFIG_API_KEY  # type: ignore
    from config import BASE_URL as CONFIG_BASE_URL  # type: ignore
    from config import MODEL as CONFIG_MODEL  # type: ignore
except Exception:  # pragma: no cover - 配置文件缺失或字段为空
    CONFIG_API_KEY = None
    CONFIG_BASE_URL = None
    CONFIG_MODEL = None


# 详细规则写在配置中，方便后续调整语气/补充条款
DEFAULT_RULES = """
目标：每手牌点数尽量靠近 21 且不超过 21，高于庄家即胜。
牌值：2-10 按面值，J/Q/K 为 10，A 计 1 或 11（取对玩家有利且不爆牌的值）。
开局：玩家与庄家各两张，庄家一明一暗。玩家先行动。
玩家动作：
- hit 要牌：从牌堆再抽一张；超过 21 视为爆牌（立即输掉该手）。
- stand 停牌：结束该手操作，轮到下一手/庄家。
- double 加倍：将当前投注翻倍，只再要一张牌后自动停牌；需有足够余额且仅限起手两张时使用。
- split 分牌：起手两张点数相同可拆成两手，需再下同额注，每手补一张后分别操作。
保险 Insurance：庄家明牌为 A 时可买保险，最多为原注一半；若庄家 Blackjack，保险赔付 2:1，否则退还保险或失效。
Blackjack：起手两张组成 21（A+10/J/Q/K），赔付 3:2，仅对未分牌的原手有效。
庄家规则：
- 庄家需补牌至 17 点或以上；软 17（含可作 11 的 A 计 17）仍需要牌。
- 庄家先结算保险，再与每手比较点数，高者胜，平局退还本金。
桌面默认：6 副牌发牌鞋；余额不足时游戏结束；下注需为正数且不超过余额。
"""


@dataclass
class DealerAgentConfig:
    """可调配置，留出 LLM 与语气/规则开关。"""

    model: str = os.getenv("LLM_MODEL") or CONFIG_MODEL or "gpt-4.1"
    api_key: Optional[str] = os.getenv("LLM_API_KEY") or CONFIG_API_KEY
    base_url: str = os.getenv("LLM_BASE_URL") or CONFIG_BASE_URL or "https://api.openai.com/v1"
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.35"))
    tone: str = "可爱、友好、偶尔俏皮"
    rules_text: str = DEFAULT_RULES
    enable_debug: bool = False  # 默认关闭，避免干扰输出；需要时可手动开启


class OpenAILLMClient:
    """薄封装，便于替换为其他提供商。

    如果没有安装 openai 或未提供密钥，会抛出 RuntimeError，
    由上层捕获后给用户提示。
    """

    def __init__(self, config: DealerAgentConfig):
        try:
            import openai  # type: ignore
        except ImportError as exc:  # pragma: no cover - 环境问题
            raise RuntimeError("缺少 openai 库，请先 pip install openai>=1.0") from exc

        if not config.api_key:
            raise RuntimeError("未检测到 LLM_API_KEY 或 config.API_KEY，请设置后再试。")

        # OpenAI Python SDK v1+ 推荐用客户端实例
        self.client = openai.OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.config = config

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]):
        """统一的对话入口，返回 ChatCompletion 对象。"""

        return self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=self.config.temperature,
        )


class DealerAgent:
    """LLM 驱动的庄家代理，负责：
    1) 维护牌局状态快照；
    2) 定义工具 schema；
    3) 将 LLM 的工具调用真正执行到 Game 上；
    4) 将执行结果反馈给 LLM，再由 LLM 输出自然语言回复。
    """

    def __init__(self, game: Game, config: Optional[DealerAgentConfig] = None):
        self.game = game
        self.config = config or DealerAgentConfig()
        self.messages: List[Dict[str, Any]] = []
        self.round_active = False
        self.hand_done: List[bool] = []  # 跟踪每手是否已停牌/爆牌/自动结束

        # 组装系统提示，包含规则与风格
        self.messages.append(
            {
                "role": "system",
                "content": self._build_system_prompt(),
            }
        )
        # 工具定义
        self.tools = self._build_tools()

        # 初始化 LLM 客户端
        self.llm = OpenAILLMClient(self.config)

    # -------------------- Prompt & Tools --------------------
    def _build_system_prompt(self) -> str:
        """生成系统提示，集中可调内容。"""

        return (
            "你是一只小猫，工作是 Blackjack 的庄家，负责和玩家聊天并通过工具驱动牌局。"
            "回复友好，可给出局势点评以及与玩家闲聊；"
            f"语气设置：{self.config.tone}。\n"
            "必须在需要游戏动作时调用相应工具（下注、要牌、停牌、加倍、分牌、保险、结算），"
            "不要擅自假设结果。\n"
            "当所有玩家手牌都已停牌或爆牌时，请调用 finish_round 完成结算。\n"
            "以下是本桌的完整规则：\n" + self.config.rules_text
        )

    def _build_tools(self) -> List[Dict[str, Any]]:
        """向 LLM 暴露的工具列表（OpenAI tools schema）。"""

        return [
            {
                "type": "function",
                "function": {
                    "name": "place_bet",
                    "description": "开始新一局并下注（第一步必须先下注）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "下注金额，需大于 0 且不超过余额",
                                "minimum": 1,
                            }
                        },
                        "required": ["amount"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "buy_insurance",
                    "description": "庄家明牌为 A 时购买保险，最多为原注的一半。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "保险金额，>0",
                            }
                        },
                        "required": ["amount"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "player_hit",
                    "description": "指定手牌要牌。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hand_index": {
                                "type": "integer",
                                "description": "手牌序号，从 0 开始，默认为当前手",
                                "minimum": 0,
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "player_stand",
                    "description": "指定手牌停牌。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hand_index": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "手牌序号，从 0 开始",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "player_double",
                    "description": "指定手牌加倍（仅起手两张且余额足够时）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hand_index": {
                                "type": "integer",
                                "minimum": 0,
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "player_split",
                    "description": "指定手牌分牌（两张点数相同且余额足够时）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hand_index": {
                                "type": "integer",
                                "minimum": 0,
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finish_round",
                    "description": "当玩家动作结束后，触发庄家补牌与结算。",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]

    # -------------------- 状态与工具实现 --------------------
    def _debug(self, message: str) -> None:
        """调试打印，方便观察工具调用。"""

        if self.config.enable_debug:
            print(f"【记录】{message}")

    def _ensure_round(self) -> None:
        if not self.round_active:
            raise ValueError("当前没有进行中的牌局，请先下注开启新一局。")

    def _state_summary(self) -> str:
        """返回当前牌局的中文摘要，提供给 LLM 参考。"""

        parts: List[str] = []
        parts.append(f"余额: {self.game.player.balance:.2f}")
        for idx, hand in enumerate(self.game.player.hands):
            status: List[str] = []
            if idx < len(self.hand_done) and self.hand_done[idx]:
                status.append("已停牌/结束")
            if hand.is_bust():
                status.append("爆牌")
            if hand.is_blackjack():
                status.append("Blackjack")
            parts.append(f"手牌#{idx}: {hand} | {'/'.join(status) if status else '进行中'}")
        if self.game.dealer.hand.cards:
            parts.append(f"庄家明牌: {self.game.dealer.hand.cards[0]}")
        else:
            parts.append("庄家尚未开局")
        return "；".join(parts)

    def place_bet(self, amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("下注金额需大于 0")
        if amount > self.game.player.balance:
            raise ValueError("余额不足，无法下注")

        # 开新局
        self.game.start_round(amount)
        self.round_active = True
        self.hand_done = [False for _ in self.game.player.hands]

        self._debug(f"place_bet(amount={amount}) -> 玩家:{self.game.player.hands[0]}, 庄家明牌:{self.game.dealer.hand.cards[0]}")
        return {
            "message": "下注成功，已发两张起手牌。",
            "player_hand": str(self.game.player.hands[0]),
            "dealer_upcard": str(self.game.dealer.hand.cards[0]),
            "balance": self.game.player.balance,
        }

    def buy_insurance(self, amount: float) -> Dict[str, Any]:
        self._ensure_round()
        upcard = self.game.dealer.hand.cards[0]
        if upcard.rank != "A":
            raise ValueError("庄家明牌不是 A，不能购买保险。")
        max_insurance = min(self.game.player.bets[0] / 2, self.game.player.balance)
        if amount <= 0 or amount > max_insurance:
            raise ValueError(f"保险金额需在 0 到 {max_insurance} 之间。")

        self.game.player.place_insurance(amount)
        self._debug(f"buy_insurance(amount={amount})")
        return {
            "message": f"已购买保险 {amount}",
            "balance": self.game.player.balance,
        }

    def player_hit(self, hand_index: int = 0) -> Dict[str, Any]:
        self._ensure_round()
        self._validate_hand_index(hand_index)

        hand = self.game.player.hands[hand_index]
        new_card = self.game.deck.draw()
        hand.add_card(new_card)

        finished = hand.is_bust() or hand.is_blackjack()
        if hand_index < len(self.hand_done):
            self.hand_done[hand_index] = finished

        self._debug(
            f"player_hit(hand_index={hand_index}) -> {new_card}, hand={hand}, done={finished}"
        )
        return {
            "card": str(new_card),
            "hand": str(hand),
            "is_bust": hand.is_bust(),
            "is_blackjack": hand.is_blackjack(),
            "next_hint": self._auto_finish_hint(),
        }

    def player_stand(self, hand_index: int = 0) -> Dict[str, Any]:
        self._ensure_round()
        self._validate_hand_index(hand_index)
        if hand_index < len(self.hand_done):
            self.hand_done[hand_index] = True
        self._debug(f"player_stand(hand_index={hand_index})")
        return {"message": "已停牌", "next_hint": self._auto_finish_hint()}

    def player_double(self, hand_index: int = 0) -> Dict[str, Any]:
        self._ensure_round()
        self._validate_hand_index(hand_index)
        hand = self.game.player.hands[hand_index]
        if len(hand.cards) != 2:
            raise ValueError("加倍仅限起手两张且未行动时使用。")
        success = self.game.handle_double(hand_index)
        if not success:
            raise ValueError("加倍失败，可能是余额不足或已无法加倍。")
        self.hand_done[hand_index] = True  # 加倍后自动停牌
        self._debug(
            f"player_double(hand_index={hand_index}) -> hand={hand}, bet={self.game.player.bets[hand_index]}"
        )
        return {
            "hand": str(hand),
            "bet": self.game.player.bets[hand_index],
            "next_hint": self._auto_finish_hint(),
        }

    def player_split(self, hand_index: int = 0) -> Dict[str, Any]:
        self._ensure_round()
        self._validate_hand_index(hand_index)
        before = len(self.game.player.hands)
        self.game.handle_split(hand_index)
        after = len(self.game.player.hands)
        # 同步 hand_done 列表，新增手牌标记为未完成
        while len(self.hand_done) < after:
            self.hand_done.append(False)
        self._debug(
            f"player_split(hand_index={hand_index}) -> hands {before} -> {after}, current={self._state_summary()}"
        )
        return {
            "message": "分牌成功，每手已各补一张。",
            "hands": [str(h) for h in self.game.player.hands],
            "balance": self.game.player.balance,
        }

    def finish_round(self) -> Dict[str, Any]:
        self._ensure_round()

        # 如果至少一手未爆，庄家需要行动；否则可直接结算
        if not all(hand.is_bust() for hand in self.game.player.hands):
            self.game.dealer_turn()

        self.game.settle_insurance()
        results = [self.game.settle_hand(i) for i in range(len(self.game.player.hands))]
        balance = self.game.player.balance

        # 重置状态
        self.round_active = False
        self.hand_done = []

        self._debug(f"finish_round() -> results={results}, balance={balance}")
        return {
            "results": results,
            "dealer_hand": str(self.game.dealer.hand),
            "balance": balance,
        }

    # -------------------- LLM 交互主入口 --------------------
    def handle_user_message(self, user_text: str) -> str:
        """外部入口：接收用户输入 -> LLM -> 可能的工具调用 -> 返回回复文本。"""

        self.messages.append({"role": "user", "content": user_text})

        while True:
            try:
                completion = self.llm.chat(self.messages, self.tools)
            except Exception as exc:  # pragma: no cover - 运行时网络/配置问题
                return f"LLM 调用失败：{exc}"

            msg = completion.choices[0].message

            # 如果大模型请求调用工具，逐一执行后继续对话
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                if hasattr(msg, "model_dump"):
                    assistant_msg = msg.model_dump(exclude_none=True)
                elif hasattr(msg, "to_dict"):
                    assistant_msg = msg.to_dict()
                else:  # 兜底，避免 SDK 版本差异
                    assistant_msg = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls,
                    }
                self.messages.append(assistant_msg)

                for call in tool_calls:
                    name = call.function.name
                    args = json.loads(call.function.arguments or "{}")
                    result = self._run_tool(name, args)
                    # 调试打印
                    self._debug(f"tool_call {name} args={args} -> {result}")
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                # 工具结果写回后继续让模型生成最终回复
                continue

            # 无工具调用即为最终回复
            content = msg.content or ""
            self.messages.append({"role": "assistant", "content": content})
            return content

    # -------------------- 工具调度辅助 --------------------
    def _run_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """根据名称分发到具体实现。"""

        try:
            if name == "place_bet":
                return self.place_bet(float(args.get("amount", 0)))
            if name == "buy_insurance":
                return self.buy_insurance(float(args.get("amount", 0)))
            if name == "player_hit":
                return self.player_hit(int(args.get("hand_index", 0)))
            if name == "player_stand":
                return self.player_stand(int(args.get("hand_index", 0)))
            if name == "player_double":
                return self.player_double(int(args.get("hand_index", 0)))
            if name == "player_split":
                return self.player_split(int(args.get("hand_index", 0)))
            if name == "finish_round":
                return self.finish_round()
        except Exception as exc:
            # 将错误信息回传给 LLM，便于它调整下一步操作
            return {"error": str(exc), "state": self._state_summary()}

        return {"error": f"未知的工具调用: {name}", "state": self._state_summary()}

    def _auto_finish_hint(self) -> str:
        """返回提示，帮助 LLM 判断是否该结算。"""

        if not self.round_active:
            return "当前无局进行"
        all_done = all(
            (hand.is_bust() or (idx < len(self.hand_done) and self.hand_done[idx]))
            for idx, hand in enumerate(self.game.player.hands)
        )
        if all_done:
            return "所有手牌已结束，可调用 finish_round 结算。"
        return "仍有手牌可行动"

    def _validate_hand_index(self, hand_index: int) -> None:
        if hand_index < 0 or hand_index >= len(self.game.player.hands):
            raise ValueError(f"hand_index {hand_index} 超出范围。")


__all__ = ["DealerAgent", "DealerAgentConfig", "DEFAULT_RULES"]
