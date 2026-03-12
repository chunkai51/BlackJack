from __future__ import annotations

import random
from typing import List

from .card import Card


class Deck:
    """牌堆类，支持 6 副牌洗牌模式和全随机抽牌模式。"""

    SUITS = ["♠", "♥", "♣", "♦"]
    RANKS = ["A"] + [str(i) for i in range(2, 11)] + ["J", "Q", "K"]
    RANK_VALUES = {
        "A": 11,  # A 初始按 11 计，后续由 Hand 调整
        "J": 10,
        "Q": 10,
        "K": 10,
        **{str(i): i for i in range(2, 11)},
    }

    def __init__(self, mode: str = "shoe"):
        # mode 可选:
        # - "shoe": 6 副牌组成的发牌鞋，耗尽自动重新洗牌
        # - "infinite": 全随机模式，每次发牌直接随机生成，不耗库存
        self.mode = mode
        self.cards: List[Card] = []
        if self.mode == "shoe":
            self._build_shoe()

    def _build_shoe(self) -> None:
        # 构建 6 副牌并洗牌
        self.cards = []
        for _ in range(6):
            for suit in self.SUITS:
                for rank in self.RANKS:
                    value = self.RANK_VALUES[rank]
                    self.cards.append(Card(suit, rank, value))
        random.shuffle(self.cards)

    def draw(self) -> Card:
        # 抽一张牌；若为鞋模式且牌堆为空则重建
        if self.mode == "shoe":
            if not self.cards:
                self._build_shoe()
            return self.cards.pop()
        # 全随机模式直接随机生成
        suit = random.choice(self.SUITS)
        rank = random.choice(self.RANKS)
        value = self.RANK_VALUES[rank]
        return Card(suit, rank, value)

