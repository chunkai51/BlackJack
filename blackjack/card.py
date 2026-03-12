from __future__ import annotations


class Card:
    """表示一张扑克牌。"""

    def __init__(self, suit: str, rank: str, value: int):
        # suit: 花色，例如 '♠', '♥', '♣', '♦'
        # rank: 点数字符，例如 'A', '2', ..., '10', 'J', 'Q', 'K'
        # value: 本张牌的基础点数（A 视为 11，JQK 为 10，其余为牌面数字）
        self.suit = suit
        self.rank = rank
        self.value = value

    def __str__(self) -> str:
        # 返回形如 "A♠" 的展示字符串
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        # 便于调试时查看
        return f"Card({self.rank}{self.suit}, value={self.value})"

