from __future__ import annotations

from typing import List

from .card import Card


class Hand:
    """玩家或庄家的手牌，负责点数计算与状态判断。"""

    def __init__(self):
        # cards: 当前手牌列表
        self.cards: List[Card] = []

    def add_card(self, card: Card) -> None:
        # 添加一张牌到手牌
        self.cards.append(card)

    def value(self) -> int:
        # 计算手牌点数，A 可作 11 或 1，尽量避免爆牌
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        # 若总点数超过 21，则将 A 由 11 降为 1，最多调整到不爆或无可调
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_blackjack(self) -> bool:
        # 首发两张且点数为 21 视为 Blackjack
        return len(self.cards) == 2 and self.value() == 21

    def is_bust(self) -> bool:
        # 点数大于 21 为爆牌
        return self.value() > 21

    def can_split(self) -> bool:
        # 判断是否可以分牌：手牌两张且点数相同
        return len(self.cards) == 2 and self.cards[0].rank == self.cards[1].rank

    def split(self) -> "Hand":
        # 执行分牌，返回新的手牌，其中包含原第二张牌
        if not self.can_split():
            raise ValueError("当前手牌不可分牌")
        new_hand = Hand()
        # 移动第二张牌到新手牌
        new_hand.add_card(self.cards.pop())
        return new_hand

    def __str__(self) -> str:
        # 将手牌列表转为字符串，例如 "A♠, 10♥ (21)"
        card_str = ", ".join(str(c) for c in self.cards)
        return f"{card_str} ({self.value()})"
