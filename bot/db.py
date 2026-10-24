"""Postgres (Supabase) access."""

from datetime import date, datetime
from decimal import Decimal

from psycopg_pool import AsyncConnectionPool

from bot import config

_pool: AsyncConnectionPool | None = None


async def open_pool() -> None:
    global _pool
    # prepare_threshold=None keeps this working behind Supabase's pgbouncer pooler.
    _pool = AsyncConnectionPool(
        config.DATABASE_URL,
        min_size=1,
        max_size=4,
        open=False,
        kwargs={"prepare_threshold": None},
    )
    # wait=True fails startup right away if the database can't be reached.
    await _pool.open(wait=True, timeout=15)


async def connection_info() -> str:
    """Where we're connected (never includes the password)."""
    async with _pool.connection() as conn:
        info = conn.info
        cur = await conn.execute("SHOW server_version")
        version = (await cur.fetchone())[0]
    return f"{info.host}:{info.port}/{info.dbname} as {info.user} (PostgreSQL {version})"


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


async def _fetchall(query: str, params: tuple = ()) -> list[tuple]:
    async with _pool.connection() as conn:
        cur = await conn.execute(query, params)
        return await cur.fetchall()


async def _fetchone(query: str, params: tuple = ()) -> tuple:
    async with _pool.connection() as conn:
        cur = await conn.execute(query, params)
        return await cur.fetchone()


async def add_expense(category: str, amount: Decimal) -> datetime:
    row = await _fetchone(
        "INSERT INTO expenses (category, amount) VALUES (%s, %s) RETURNING created_at",
        (category, amount),
    )
    return row[0]


async def add_income(source: str, amount: Decimal) -> datetime:
    row = await _fetchone(
        "INSERT INTO incomes (source, amount) VALUES (%s, %s) RETURNING created_at",
        (source, amount),
    )
    return row[0]


async def add_investment(amount: Decimal) -> datetime:
    row = await _fetchone(
        "INSERT INTO investments (amount) VALUES (%s) RETURNING created_at",
        (amount,),
    )
    return row[0]


async def total_investments() -> Decimal:
    row = await _fetchone("SELECT COALESCE(SUM(amount), 0) FROM investments")
    return row[0]


async def expenses_by_category(start: datetime, end: datetime) -> list[tuple[str, Decimal]]:
    return await _fetchall(
        """
        SELECT category, SUM(amount) FROM expenses
        WHERE created_at >= %s AND created_at < %s
        GROUP BY category ORDER BY SUM(amount) DESC
        """,
        (start, end),
    )


async def incomes_by_source(start: datetime, end: datetime) -> list[tuple[str, Decimal]]:
    return await _fetchall(
        """
        SELECT source, SUM(amount) FROM incomes
        WHERE created_at >= %s AND created_at < %s
        GROUP BY source ORDER BY SUM(amount) DESC
        """,
        (start, end),
    )


async def monthly_expense_totals() -> dict[date, Decimal]:
    rows = await _fetchall(
        """
        SELECT date_trunc('month', created_at AT TIME ZONE 'Asia/Jerusalem')::date AS month,
               SUM(amount)
        FROM expenses GROUP BY month
        """
    )
    return dict(rows)


async def get_budgets() -> dict[date, Decimal]:
    return dict(await _fetchall("SELECT month, amount FROM budgets"))


async def set_budget(month: date, amount: Decimal) -> None:
    async with _pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO budgets (month, amount) VALUES (%s, %s)
            ON CONFLICT (month) DO UPDATE SET amount = EXCLUDED.amount
            """,
            (month, amount),
        )
