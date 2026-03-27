from __future__ import annotations

import time

from .deck import Deck
from .player import Player
from .dealer import Dealer


class Game:
    """管理整场 Blackjack 的流程（单人对庄家）。"""

    def __init__(self, player_name: str = "Player", deck_mode: str = "shoe"):
        # deck_mode: "shoe" 表示 6 副牌发牌鞋；"infinite" 表示全随机模式
        self.deck = Deck(mode=deck_mode)
        self.player = Player(player_name)
        self.dealer = Dealer()

    def start_round(self, bet: float) -> None:
        # 开始一局：重置手牌并处理开局发牌与下注
        self.player.reset_hands()
        self.dealer.reset_hand()

        # 记录下注
        self.player.place_bet(bet, hand_index=0)

        # 开局发牌：玩家、庄家各两张
        for i in range(2):
            card_p = self.deck.draw()
            self.player.hands[0].add_card(card_p)
            print(f"发给玩家第{i+1}张: {card_p}")
            time.sleep(0.8)

            card_d = self.deck.draw()
            self.dealer.hand.add_card(card_d)
            who = "庄家明牌" if i == 0 else "庄家底牌"
            print(f"{who}: {card_d if i == 0 else '🂠'}")
            time.sleep(0.8)

    def offer_insurance(self) -> bool:
        # 当庄家明牌为 A 时提供保险，返回是否购买
        upcard = self.dealer.hand.cards[0]
        if upcard.rank != "A":
            return False
        max_insurance = min(self.player.bets[0] / 2, self.player.balance)
        if max_insurance <= 0:
            return False
        try:
            choice = input(f"庄家明牌为 A，是否购买保险 (最多 {max_insurance})? [y/n] ").strip().lower()
        except EOFError:
            return False
        if choice == "y":
            while True:
                try:
                    amount_str = input("请输入保险金额: ")
                    amount = float(amount_str)
                    if amount <= 0 or amount > max_insurance:
                        print(f"保险金额需在 0 到 {max_insurance} 之间")
                        continue
                    self.player.place_insurance(amount)
                    print(f"已购买保险 {amount}")
                    return True
                except ValueError as exc:
                    print(f"输入错误: {exc}")
                except EOFError:
                    return False
        return False

    def handle_split(self, hand_index: int) -> None:
        # 处理玩家选择分牌的流程（可多次分牌）
        hand = self.player.hands[hand_index]
        if not hand.can_split():
            print("当前手牌不可分牌")
            return
        bet = self.player.bets[hand_index]
        if bet > self.player.balance:
            print("余额不足，无法分牌")
            return
        # 创建新手牌并补一张牌给两个手牌
        new_hand = hand.split()
        self.player.balance -= bet
        self.player.add_hand(new_hand, bet)
        hand.add_card(self.deck.draw())
        new_hand.add_card(self.deck.draw())
        print("分牌成功，当前手牌数:", len(self.player.hands))

    def handle_double(self, hand_index: int) -> bool:
        # 处理加倍逻辑，成功返回 True
        hand = self.player.hands[hand_index]
        if len(hand.cards) != 2:
            print("加倍仅限起手两张时可用。")
            return False
        if hand.is_bust():
            print("当前手牌已爆牌，无法加倍。")
            return False
        bet = self.player.bets[hand_index]
        if bet > self.player.balance:
            print("余额不足，无法加倍")
            return False
        self.player.balance -= bet
        self.player.bets[hand_index] += bet
        # 加倍后只允许再拿一张牌，同时打印补到的牌与当前手牌
        new_card = self.deck.draw()
        hand.add_card(new_card)
        print(f"已加倍，补到 {new_card}，当前手牌: {hand}，当前投注 {self.player.bets[hand_index]}")
        return True

    def player_turn(self, hand_index: int) -> None:
        # 处理玩家对单手牌的操作：要牌、停牌、分牌、加倍
        hand = self.player.hands[hand_index]
        while True:
            print(f"当前手牌: {hand}")
            if hand.is_blackjack():
                print("Blackjack!")
                return
            if hand.is_bust():
                print("爆牌！")
                return
            options = ["h 要牌", "s 停牌"]
            if hand.can_split() and self.player.balance >= self.player.bets[hand_index]:
                options.append("p 分牌")
            if len(hand.cards) == 2 and self.player.balance >= self.player.bets[hand_index]:
                options.append("d 加倍")
            try:
                choice = input(f"选择操作 ({', '.join(options)}): ").strip().lower()
            except EOFError:
                choice = "s"
            if choice == "h":
                hand.add_card(self.deck.draw())
            elif choice == "s":
                return
            elif choice == "p" and "p 分牌" in options:
                self.handle_split(hand_index)
                # 分牌后需对新手牌也依次处理，外层循环会覆盖
                return
            elif choice == "d" and "d 加倍" in options:
                doubled = self.handle_double(hand_index)
                if doubled:
                    # 加倍后只能再要一张再停
                    return
            else:
                print("无效选择，请重新输入")

    def dealer_turn(self) -> None:
        # 庄家按规则补牌
        print(f"庄家明牌: {self.dealer.hand.cards[0]}")
        print("庄家补牌中...")
        self.dealer.play(self.deck)
        print(f"庄家最终手牌: {self.dealer.hand}")

    def settle_hand(self, hand_index: int) -> str:
        # 结算单手牌结果并返回描述
        player_hand = self.player.hands[hand_index]
        dealer_hand = self.dealer.hand

        if player_hand.is_bust():
            self.player.lose(hand_index)
            return "玩家爆牌，输"
        if dealer_hand.is_bust():
            self.player.win(hand_index)
            return "庄家爆牌，玩家赢"
        if player_hand.is_blackjack() and not dealer_hand.is_blackjack():
            self.player.win(hand_index, ratio=1.5)
            return "玩家 Blackjack，赔付 3:2"
        if dealer_hand.is_blackjack() and not player_hand.is_blackjack():
            self.player.lose(hand_index)
            return "庄家 Blackjack，输"

        player_value = player_hand.value()
        dealer_value = dealer_hand.value()
        if player_value > dealer_value:
            self.player.win(hand_index)
            return "点数更高，玩家赢"
        if player_value < dealer_value:
            self.player.lose(hand_index)
            return "点数更低，玩家输"
        self.player.push(hand_index)
        return "平局，退还本金"

    def settle_insurance(self) -> None:
        # 根据庄家是否 Blackjack 结算保险
        dealer_blackjack = self.dealer.hand.is_blackjack()
        if dealer_blackjack:
            gain = self.player.settle_insurance_win()
            if gain:
                print(f"保险赔付 {gain}")
        else:
            refund = self.player.refund_insurance()
            if refund:
                print(f"庄家无 Blackjack，退还保险 {refund}")

    def play_round(self) -> None:
        # CLI 单局流程：下注 -> 发牌 -> 保险 -> 玩家回合 -> 庄家回合 -> 结算
        while True:
            try:
                bet_input = input("请输入本局下注金额（输入 q 退出本局/游戏）: ").strip().lower()
            except EOFError:
                return "quit"
            if bet_input == "q":
                return "quit"
            try:
                bet = float(bet_input)
            except ValueError:
                print("输入无效，请重新输入数字。")
                continue
            if bet <= 0:
                print("下注需大于 0，请重新输入。")
                continue
            if bet > self.player.balance:
                print("余额不足，请重新输入不超过余额的下注。")
                continue
            break

        self.start_round(bet)
        print(f"你的余额: {self.player.balance}")
        print(f"你的手牌: {self.player.hands[0]}")
        print(f"庄家明牌: {self.dealer.hand.cards[0]}")

        # 保险
        self.offer_insurance()

        # 若庄家与玩家都可能 Blackjack，先检查
        if self.dealer.hand.is_blackjack():
            print("庄家 Blackjack!")
            self.settle_insurance()
            # 玩家可能也有 Blackjack
            result = self.settle_hand(0)
            print(result)
            print(f"余额: {self.player.balance}")
            print("-" * 40)
            return

        # 处理玩家所有手牌（分牌后可能多手）
        idx = 0
        while idx < len(self.player.hands):
            self.player_turn(idx)
            # 分牌可能在 player_turn 中增加手牌，循环自然覆盖
            idx += 1

        # 如果所有手牌都爆牌，庄家无需行动
        if all(hand.is_bust() for hand in self.player.hands):
            self.settle_insurance()
            for i in range(len(self.player.hands)):
                print(self.settle_hand(i))
            print(f"余额: {self.player.balance}")
            print("-" * 40)
            return

        # 庄家行动并结算
        self.dealer_turn()
        self.settle_insurance()
        for i in range(len(self.player.hands)):
            print(self.settle_hand(i))
        print(f"余额: {self.player.balance}")
        print("-" * 40)
