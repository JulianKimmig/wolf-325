"""Asynchronous execution helpers for blocking external resource operations."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")


async def run_in_worker(function: Callable[_P, _R], *args: _P.args) -> _R:
    """Run one blocking call in an explicitly owned worker thread.

    Args:
        function: Blocking callable that does not access event-loop-owned state.
        *args: Positional arguments passed to ``function``.

    Returns:
        The callable result after the worker has completed and shut down.
    """
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wolf-file")
    try:
        operation = functools.partial(function, *args)
        return await loop.run_in_executor(executor, operation)
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
