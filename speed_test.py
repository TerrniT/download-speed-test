#!/usr/bin/env python3
"""Измеряет скорость скачивания по URL: 10 последовательных запросов."""

import argparse
import sys
import time
import urllib.request


def format_bytes(n: float) -> str:
    if n < 1024:
        return f"{n:.0f} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.2f} KB"
    if n < 1024 ** 3:
        return f"{n / (1024 ** 2):.2f} MB"
    return f"{n / (1024 ** 3):.2f} GB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Делает 10 последовательных запросов к URL и считает скорость скачивания."
    )
    parser.add_argument("url", help="Адрес для запроса (например, тяжёлая картинка)")
    parser.add_argument("-n", "--count", type=int, default=10, help="Количество запросов (по умолчанию 10)")
    args = parser.parse_args()

    if args.count <= 0:
        print("Количество запросов должно быть больше 0", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        args.url,
        headers={"User-Agent": "download-speed-test/1.0"},
    )

    times = []
    total_bytes = 0

    print(f"URL: {args.url}")
    print(f"Запросов: {args.count}")
    print("-" * 40)

    for i in range(1, args.count + 1):
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request) as response:
                data = response.read()
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{args.count}] ОШИБКА: {exc}", file=sys.stderr)
            return 1
        elapsed = time.perf_counter() - start
        size = len(data)
        times.append(elapsed)
        total_bytes += size
        speed_mbps = (size * 8) / elapsed / 1_000_000 if elapsed > 0 else float("inf")
        print(
            f"[{i}/{args.count}] {format_bytes(size):>10} | "
            f"{elapsed:6.3f} с | {speed_mbps:7.2f} Мбит/с"
        )

    total_time = sum(times)
    avg_time = total_time / len(times)
    overall_mbps = (total_bytes * 8) / total_time / 1_000_000 if total_time > 0 else float("inf")
    overall_mbs = total_bytes / total_time / (1024 ** 2) if total_time > 0 else float("inf")

    print("-" * 40)
    print(f"Среднее время запроса: {avg_time:.3f} с")
    print(f"Общий объём данных:    {format_bytes(total_bytes)} ({total_bytes} байт)")
    print(f"Общее время:           {total_time:.3f} с")
    print(f"Скорость скачивания:   {overall_mbps:.2f} Мбит/с ({overall_mbs:.2f} MB/s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
