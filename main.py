"""阶段一：命令行版 Blackjack，仅实现规则与单人模式。"""

from blackjack.game import Game


def main() -> None:
    # 创建游戏实例，可选择 6 副牌模式("shoe") 或全随机模式("infinite")
    try:
        mode = input("选择牌堆模式 [shoe=6副牌 / infinite=全随机] (默认 shoe): ").strip().lower()
    except EOFError:
        mode = "shoe"
    if mode not in {"shoe", "infinite"}:
        mode = "shoe"
    try:
        player_name = input("请输入玩家姓名 (默认 Player): ").strip() or "Player"
    except EOFError:
        player_name = "Player"

    game = Game(player_name=player_name, deck_mode=mode)
    print("欢迎来到 Blackjack！输入 q 退出，其他键继续。")

    while True:
        try:
            cmd = input("按回车开始新一局，或输入 q 退出: ").strip().lower()
        except EOFError:
            cmd = "q"
        if cmd == "q":
            print("感谢游玩，再见！")
            break
        if game.player.balance <= 0:
            print("余额不足，游戏结束。")
            break
        game.play_round()


if __name__ == "__main__":
    main()
