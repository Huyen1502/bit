"""Simple Python file template."""

import argparse


def greet(name: str) -> None:
    """Print a greeting to the given name."""
    print(f"Hello, {name}!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Greet a user.")
    parser.add_argument("-n", "--name", default="World", help="Name to greet")
    args = parser.parse_args()
    greet(args.name)


if __name__ == "__main__":
    main()