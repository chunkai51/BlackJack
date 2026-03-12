from __future__ import annotations

from typing import List, Optional

from .hand import Hand


class Player:
    """玩家类，管理资金、手牌与下注。"""

    def __init__(self, name: str, balance: float = 1000.0):
        # name: 玩家昵称
        # balance: 玩家余额，默认 1000
        self.name = name
        self.balance = balance
        # hands: 可能存在多手牌（分牌后），每手牌对应一个下注金额
        self.hands: List[Hand] = [Hand()]
        self.bets: List[float] = [0.0]
        self.insurance_bet: float = 0.0

    def reset_hands(self) -> None:
        # 开局前清空所有手牌与下注，仅保留一手空牌
        self.hands = [Hand()]
        self.bets = [0.0]
        self.insurance_bet = 0.0

    def place_bet(self, amount: float, hand_index: int = 0) -> None:
        # 为指定手牌下注，扣除余额
        if amount <= 0:
            raise ValueError("下注金额需大于 0")
        if amount > self.balance:
            raise ValueError("余额不足，无法下注")
        self.balance -= amount
        self.bets[hand_index] = amount

    def add_hand(self, hand: Hand, bet: float) -> None:
        # 增加一手新牌（分牌后使用），并为其记录对应下注
        self.hands.append(hand)
        self.bets.append(bet)

    def win(self, hand_index: int, ratio: float = 1.0) -> float:
        # 按照赔付比例结算指定手牌胜利（默认 1:1），返回赢得金额
        win_amount = self.bets[hand_index] * (1 + ratio)
        self.balance += win_amount
        return win_amount

    def lose(self, hand_index: int) -> float:
        # 失败不返还本金，返回损失金额（用于统计）
        return self.bets[hand_index]

    def push(self, hand_index: int) -> float:
        # 和局退回本金
        refund = self.bets[hand_index]
        self.balance += refund
        return refund

    def place_insurance(self, amount: float) -> None:
        # 购买保险，扣除余额（保险上限由外部控制）
        if amount <= 0:
            raise ValueError("保险金额需大于 0")
        if amount > self.balance:
            raise ValueError("余额不足，无法购买保险")
        self.balance -= amount
        self.insurance_bet = amount

    def settle_insurance_win(self) -> float:
        # 庄家有 Blackjack 时保险赔付 2:1
        if self.insurance_bet <= 0:
            return 0.0
        win_amount = self.insurance_bet * 3
        self.balance += win_amount
        self.insurance_bet = 0.0
        return win_amount

    def refund_insurance(self) -> float:
        # 庄家无 Blackjack 时退回保险本金
        refund = self.insurance_bet
        self.balance += refund
        self.insurance_bet = 0.0
        return refund

