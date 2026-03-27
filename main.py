"""AI 庄家版 Blackjack 入口。

玩家通过自然语言与庄家对话，庄家会调用工具驱动牌局。
LLM 配置通过环境变量 LLM_API_KEY / LLM_MODEL / LLM_BASE_URL 等注入。
"""

from blackjack.agent import DealerAgent, DealerAgentConfig
from blackjack.game import Game


def main() -> None:
    # 提示：保留牌堆模式参数，方便后续扩展
    deck_mode = "shoe"  # 默认 6 副牌发牌鞋

    config = DealerAgentConfig()
    game = Game(player_name="Player", deck_mode=deck_mode)

    try:
        agent = DealerAgent(game, config)
    except RuntimeError as exc:
        print(
            f"启动失败：{exc}\n"
            "请在 config.py 的 API_KEY 写入密钥，或设置环境变量 LLM_API_KEY/LLM_MODEL/LLM_BASE_URL 后重试。"
        )
        return

    print("欢迎来到 AI 庄家 Blackjack！直接聊天即可，输入 q/quit 退出。")
    if not config.api_key:
        print("提示：当前未检测到 API Key，请在 config.py 或环境变量中配置后再启动。")

    while True:
        try:
            user_text = input("你: ").strip()
        except EOFError:
            break
        if user_text.lower() in {"q", "quit", "exit"}:
            print("感谢游玩，再见！")
            break
        if not user_text:
            continue
        reply = agent.handle_user_message(user_text)
        print(f"庄家: {reply}")


if __name__ == "__main__":
    main()
