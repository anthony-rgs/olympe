from typing import AsyncGenerator

import psycopg
from psycopg.rows import dict_row

from .config import DATABASE_URL


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
  async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
    yield conn
