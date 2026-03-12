from __future__ import annotations

from .hand import Hand
from .deck import Deck


class Dealer:
    """庄家类，遵循软 17 要牌规则。"""

    def __init__(self):
        # 庄家只有一手牌
        self.hand = Hand()

    def reset_hand(self) -> None:
        # 开局前重置手牌
        self.hand = Hand()

    def should_hit(self) -> bool:
        # 判断是否继续要牌：软 17（含作 11 的 A）也要牌
        value = self.hand.value()
        # 判断是否为软手：有 A 且将其算作 11 时不爆
        soft = any(card.rank == "A" for card in self.hand.cards) and value <= 21
        return value < 17 or (value == 17 and soft)

    def play(self, deck: Deck) -> None:
        # 庄家按照规则补牌直至停牌
        while self.should_hit():
            self.hand.add_card(deck.draw())

