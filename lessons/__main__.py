"""
Run the lessons.

    python -m lessons          list the lessons
    python -m lessons 3        run lesson 3
    python -m lessons all      run every lesson in order
"""
from __future__ import annotations

import sys

from . import discover
from ._kit import LessonError, course_settings

USAGE = "usage: python -m lessons [NUMBER | all]"


def print_index() -> None:
    print("MQTT hands-on course. Pick a lesson:\n")
    for lesson in discover():
        print(f"  {lesson.number:2d}  {lesson.title}")
    print(f"\n{USAGE}")
    print("(in Docker: docker compose run --rm course NUMBER)")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    lessons = {lesson.number: lesson for lesson in discover()}
    if not args:
        print_index()
        return 0
    if len(args) != 1 or not (args[0] == "all" or args[0].isdigit()):
        print(USAGE, file=sys.stderr)
        return 2
    chosen = list(lessons.values()) if args[0] == "all" else [lessons.get(int(args[0]))]
    if chosen == [None]:
        print(f"There is no lesson {args[0]}. Run without arguments to list them.", file=sys.stderr)
        return 2

    settings = course_settings()
    for lesson in chosen:
        heading = f"Lesson {lesson.number}: {lesson.title}"
        print(f"\n{heading}\n{'=' * len(heading)}")
        print(f"Broker: {settings.describe()}  -  read along: lessons/{lesson.module_name}.md")
        try:
            lesson.run(settings)
        except LessonError as error:
            print(f"\n{error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
