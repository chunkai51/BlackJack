# Blackjack CLI 阶段说明文档

本文帮助你快速读懂代码结构、主要类与函数的职责，以及命令行玩法流程。代码面向 Python 初学者，注释均为中文。

## 目录结构
- `main.py`：程序入口，处理模式选择、玩家名输入与整局循环。
- `blackjack/`
  - `card.py`：`Card` 单张牌对象，包含花色、点数与显示。
  - `deck.py`：`Deck` 牌堆，支持 6 副牌发牌鞋（`shoe`）和全随机模式（`infinite`）。
  - `hand.py`：`Hand` 手牌，负责点数计算、Blackjack/爆牌/可分牌判断，支持分牌。
  - `player.py`：`Player` 玩家，管理余额、每手牌的下注与保险。
  - `dealer.py`：`Dealer` 庄家，执行“软 17 要牌”规则。
  - `game.py`：`Game` 整局流程控制（下注、发牌、玩家动作、庄家动作、保险、结算）。

## 核心类与关键方法
### Card（`card.py`）
- `__str__`：返回如 `A♠` 的展示字符串。

### Deck（`deck.py`）
- `__init__(mode)`：`shoe` 创建 6 副牌并洗牌；`infinite` 表示每次抽牌随机生成。
- `draw()`：从牌堆取一张；`shoe` 模式牌空会自动重建并洗牌。

### Hand（`hand.py`）
- `add_card(card)`：向手牌加入一张牌。
- `value()`：计算总点数，自动把 A 从 11 调整为 1 以避免爆牌。
- `is_blackjack()`：首发两张即 21。
- `is_bust()`：点数 > 21。
- `can_split()` / `split()`：判断并执行分牌，生成新 `Hand` 携带第二张牌。
- `__str__`：打印当前手牌及点数，例如 `A♠, 10♥ (21)`。

### Player（`player.py`）
- `place_bet(amount)`：为对应手牌下注并扣款。
- `add_hand(hand, bet)`：分牌后记录新手牌与同额下注。
- `win/lose/push()`：按 1:1 或 3:2（Blackjack）结算，平局退本金。
- `place_insurance()` / `settle_insurance_win()` / `refund_insurance()`：处理保险购买、赔付或退款。

### Dealer（`dealer.py`）
- `should_hit()`：软 17（含把 A 计为 11 的 17 点）仍要牌。
- `play(deck)`：根据规则自动补牌至停牌。

### Game（`game.py`）
- `start_round(bet)`：重置手牌、记录下注、发起始两张牌。
- `offer_insurance()`：庄家明牌为 A 时询问保险，自动校验额度。
- `handle_split()`：执行分牌，扣除同额下注，并分别补一张牌。
- `handle_double()`：加倍扣款后只补一张，立即打印补到的牌与当前手牌。
- `player_turn()`：循环处理玩家动作（要牌/停牌/分牌/加倍）；无效输入会提示重试。
- `dealer_turn()`：展示庄家明牌，按规则补牌。
- `settle_hand()`：比较点数，决定输赢/平局，含 Blackjack 特殊赔付。
- `settle_insurance()`：根据庄家是否 Blackjack 结算保险。
- `play_round()`：整局管线：下注（可输入 `q` 退出）、发牌、保险、玩家多手处理、庄家行动、结算，每局末打印分割线。

## 交互流程（`main.py`）
1. 选择牌堆模式：回车默认 `shoe`，可输入 `infinite`。
2. 输入玩家姓名：回车默认 `Player`。
3. 每局：在下注提示输入数字，或输入 `q` 直接退出游戏。
4. 发牌后可按提示选择：`h` 要牌，`s` 停牌，`p` 分牌（牌值相同且余额充足），`d` 加倍（首两张且余额充足）。
5. 庄家按软 17 规则补牌，随后结算与保险处理，打印余额与分割线。

## 规则覆盖说明
- 软 17 要牌：`Dealer.should_hit` 中实现。
- 无限分牌：`handle_split` 不限制次数，余额充足即可继续分。
- 保险：庄家明牌 A 时提供，赔付 2:1，若庄家无 Blackjack 退回保险金。
- 6 副牌 / 全随机：通过 `Deck(mode)` 切换。

## 运行
```bash
python3 main.py
```
在提示中完成模式选择、姓名、下注即可开始。非交互或 EOF 情况会安全退出，不会抛异常。

如需继续迭代（多玩家、持久化到 Firebase、Web 前端等），可以在此基础上扩展。
