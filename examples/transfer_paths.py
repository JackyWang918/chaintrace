"""Offline M2 model: compare transfer and transferFrom state changes."""

from dataclasses import dataclass


UNIT = 10**6  # Hypothetical token with 6 decimals; amounts stay integers.


@dataclass
class State:
    a: int = 10 * UNIT
    b: int = 0
    c: int = 0
    allowance_ab: int = 3 * UNIT


def transfer_from_a(state: State, amount: int) -> None:
    if state.a < amount:
        raise ValueError("A balance is insufficient")
    state.a -= amount
    state.c += amount


def b_transfer_from_a(state: State, amount: int) -> None:
    if state.a < amount or state.allowance_ab < amount:
        raise ValueError("A balance or B allowance is insufficient")
    state.a -= amount
    state.c += amount
    state.allowance_ab -= amount


def show(label: str, state: State) -> None:
    print(
        f"{label}: A={state.a // UNIT}, B={state.b // UNIT}, "
        f"C={state.c // UNIT}, allowance(A,B)={state.allowance_ab // UNIT} USDC"
    )


direct = State()
transfer_from_a(direct, 2 * UNIT)
show("A calls transfer(C,2)", direct)

delegated = State()
b_transfer_from_a(delegated, 2 * UNIT)
show("B calls transferFrom(A,C,2)", delegated)

sequential = State()
transfer_from_a(sequential, 2 * UNIT)
b_transfer_from_a(sequential, 2 * UNIT)
show("Both calls in sequence", sequential)

invalid = State()
try:
    b_transfer_from_a(invalid, 4 * UNIT)
except ValueError as exc:
    print(f"Rejected transferFrom(A,C,4): {exc}")
show("After rejected call", invalid)
