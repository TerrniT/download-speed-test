#!/usr/bin/env python3
"""Измеряет скорость скачивания по заданному URL и генерирует HTML-отчёт."""

import argparse
import html
import http.server
import socketserver
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RequestResult:
    """Результат одного запроса."""

    size: int  # размер ответа в байтах
    elapsed: float  # время запроса в секундах


class ByteFormatter:
    """Форматирование объёма данных для вывода в консоль."""

    @staticmethod
    def format_bytes(n: float) -> str:
        if n < 1024:
            return f"{n:.0f} B"
        if n < 1024 ** 2:
            return f"{n / 1024:.2f} KB"
        if n < 1024 ** 3:
            return f"{n / (1024 ** 2):.2f} MB"
        return f"{n / (1024 ** 3):.2f} GB"


class DownloadSpeedTester:
    """Выполняет серию последовательных запросов и считает скорость скачивания."""

    def __init__(self, url: str, count: int = 10):
        self.url = url
        self.count = count
        self.request = urllib.request.Request(
            url, headers={"User-Agent": "download-speed-test/1.0"}
        )
        self.results: list[RequestResult] = []

    def measure_one(self) -> RequestResult:
        """Выполняет один запрос и возвращает его результат."""
        start = time.perf_counter()
        with urllib.request.urlopen(self.request) as response:
            data = response.read()
        elapsed = time.perf_counter() - start
        return RequestResult(size=len(data), elapsed=elapsed)

    def run(self) -> list[RequestResult]:
        """Выполняет все запросы последовательно и сохраняет результаты."""
        self.results = []
        for _ in range(self.count):
            self.results.append(self.measure_one())
        return self.results

    @property
    def total_bytes(self) -> int:
        return sum(r.size for r in self.results)

    @property
    def total_time(self) -> float:
        return sum(r.elapsed for r in self.results)

    @property
    def average_time(self) -> float:
        if not self.results:
            return 0.0
        return self.total_time / len(self.results)

    @property
    def speed_mbps(self) -> float:
        if self.total_time <= 0:
            return float("inf")
        return (self.total_bytes * 8) / self.total_time / 1_000_000

    @property
    def speed_mbs(self) -> float:
        if self.total_time <= 0:
            return float("inf")
        return self.total_bytes / self.total_time / (1024 ** 2)


class ConsoleReporter:
    """Печатает результаты измерения в консоль."""

    def __init__(self, tester: DownloadSpeedTester):
        self.tester = tester

    def print_header(self) -> None:
        print(f"URL: {self.tester.url}")
        print(f"Запросов: {self.tester.count}")
        print("-" * 40)

    def print_result(self, index: int, result: RequestResult) -> None:
        speed = (
            (result.size * 8) / result.elapsed / 1_000_000
            if result.elapsed > 0
            else float("inf")
        )
        print(
            f"[{index}/{self.tester.count}] {ByteFormatter.format_bytes(result.size):>10} | "
            f"{result.elapsed:6.3f} с | {speed:7.2f} Мбит/с"
        )

    def print_summary(self) -> None:
        print("-" * 40)
        print(f"Среднее время запроса: {self.tester.average_time:.3f} с")
        print(f"Общий объём данных:    {ByteFormatter.format_bytes(self.tester.total_bytes)} "
              f"({self.tester.total_bytes} байт)")
        print(f"Общее время:           {self.tester.total_time:.3f} с")
        print(f"Скорость скачивания:   {self.tester.speed_mbps:.2f} Мбит/с "
              f"({self.tester.speed_mbs:.2f} MB/s)")


class HtmlReportGenerator:
    """Генерирует HTML-отчёт по результатам измерения."""

    @staticmethod
    def generate(tester: DownloadSpeedTester, path: Path) -> Path:
        rows = []
        for i, result in enumerate(tester.results, start=1):
            speed = (
                (result.size * 8) / result.elapsed / 1_000_000
                if result.elapsed > 0
                else float("inf")
            )
            rows.append(
                "<tr>"
                f"<td>{i}</td>"
                f"<td>{result.size}</td>"
                f"<td>{ByteFormatter.format_bytes(result.size)}</td>"
                f"<td>{result.elapsed:.3f}</td>"
                f"<td>{speed:.2f}</td>"
                "</tr>"
            )

        document = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Отчёт о скорости скачивания</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; color: #222; }}
  h1 {{ margin-bottom: 0.5rem; }}
  .meta {{ color: #555; margin-bottom: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: right; }}
  th {{ background: #f5f5f5; text-align: center; }}
  td:first-child, th:first-child {{ text-align: center; }}
  .summary {{ margin-top: 1.5rem; }}
  .summary p {{ margin: 0.25rem 0; }}
</style>
</head>
<body>
<h1>Отчёт о скорости скачивания</h1>
<p class="meta">URL: {html.escape(tester.url)}<br>Количество запросов: {tester.count}</p>
<table>
<thead>
<tr><th>#</th><th>Байты</th><th>Объём</th><th>Время, с</th><th>Мбит/с</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
<div class="summary">
<p><strong>Среднее время запроса:</strong> {tester.average_time:.3f} с</p>
<p><strong>Общий объём данных:</strong> {ByteFormatter.format_bytes(tester.total_bytes)} ({tester.total_bytes} байт)</p>
<p><strong>Общее время:</strong> {tester.total_time:.3f} с</p>
<p><strong>Скорость скачивания:</strong> {tester.speed_mbps:.2f} Мбит/с ({tester.speed_mbs:.2f} MB/s)</p>
</div>
</body>
</html>
"""
        path.write_text(document, encoding="utf-8")
        return path


class ReportServer:
    """HTTP-сервер, отдающий сгенерированный HTML-отчёт."""

    def __init__(self, content: str, port: int):
        self.content = content.encode("utf-8")
        self.port = port

    def serve_forever(self) -> None:
        handler_class = self._make_handler()
        with socketserver.ThreadingTCPServer(("0.0.0.0", self.port), handler_class) as httpd:
            httpd.allow_reuse_address = True
            print(f"Веб-сервер запущен: http://localhost:{self.port}/")
            print("Нажмите Ctrl+C для остановки.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nСервер остановлен.")

    def _make_handler(self):
        content = self.content

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format, *args):
                return

        return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Делает последовательные запросы к URL, считает скорость скачивания "
                    "и генерирует HTML-отчёт."
    )
    parser.add_argument("url", help="Адрес для запроса (например, тяжёлая картинка)")
    parser.add_argument("-n", "--count", type=int, default=10,
                        help="Количество запросов (по умолчанию 10)")
    parser.add_argument("-r", "--report", default="report.html",
                        help="Путь к HTML-отчёту (по умолчанию report.html)")
    parser.add_argument("-p", "--port", type=int, default=8000,
                        help="Порт веб-сервера (по умолчанию 8000)")
    parser.add_argument("--no-serve", action="store_true",
                        help="Не запускать веб-сервер, только сгенерировать отчёт")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count <= 0:
        print("Количество запросов должно быть больше 0", file=sys.stderr)
        return 2

    tester = DownloadSpeedTester(args.url, args.count)
    reporter = ConsoleReporter(tester)

    reporter.print_header()
    for i in range(1, args.count + 1):
        try:
            result = tester.measure_one()
            tester.results.append(result)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{args.count}] ОШИБКА: {exc}", file=sys.stderr)
            return 1
        reporter.print_result(i, result)

    reporter.print_summary()

    report_path = HtmlReportGenerator.generate(tester, Path(args.report))
    print(f"HTML-отчёт сохранён: {report_path.resolve()}")

    if args.no_serve:
        return 0

    content = report_path.read_text(encoding="utf-8")
    server = ReportServer(content, args.port)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
