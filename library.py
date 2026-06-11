#!/usr/bin/env python3
"""
typedb-library — a minimal TypeDB-backed book library CLI.

Commands
--------
  add-book    <isbn> <title> <year> [genre]
  add-author  <name> [birth_year]
  link        <author_name> <isbn>          (creates a 'wrote' relation)
  list-books  [--author <name>]
  list-authors
  get-book    <isbn>
  delete-book <isbn>
  delete-author <name>
"""

import argparse
import sys
from typedb.driver import (
    TypeDB,
    Credentials,
    DriverOptions,
    DriverTlsConfig,
    TransactionType,
    TypeDBDriverException,
)

DB_NAME = "library"
ADDRESS  = TypeDB.DEFAULT_ADDRESS




def get_driver():
    return TypeDB.driver(
        ADDRESS,
        Credentials("admin", "password"),
        DriverOptions(DriverTlsConfig.disabled()),
    )


def ensure_db(driver):
    if not driver.databases.contains(DB_NAME):
        driver.databases.create(DB_NAME)
        print(f"[init] Created database '{DB_NAME}'.")
        _load_schema(driver)
    return DB_NAME


def _load_schema(driver):
    schema_path = "schema.tql"
    with open(schema_path) as f:
        schema = f.read()
    with driver.transaction(DB_NAME, TransactionType.SCHEMA) as tx:
        tx.query(schema).resolve()
        tx.commit()
    print("[init] Schema loaded.")



def add_book(driver, isbn, title, year, genre):
    with driver.transaction(DB_NAME, TransactionType.WRITE) as tx:
        genre_clause = f', has genre "{genre}"' if genre else ""
        q = (
            f'insert $b isa book, '
            f'has isbn "{isbn}", '
            f'has title "{title}", '
            f'has year {year}'
            f'{genre_clause};'
        )
        tx.query(q).resolve()
        tx.commit()
    print(f"[ok] Book added: '{title}' (ISBN {isbn})")


def add_author(driver, name, birth_year):
    with driver.transaction(DB_NAME, TransactionType.WRITE) as tx:
        birth_clause = f", has birth-year {birth_year}" if birth_year else ""
        q = f'insert $a isa author, has name "{name}"{birth_clause};'
        tx.query(q).resolve()
        tx.commit()
    print(f"[ok] Author added: {name}")


def link(driver, author_name, isbn):
    with driver.transaction(DB_NAME, TransactionType.WRITE) as tx:
        q = (
            f'match '
            f'$a isa author, has name "{author_name}"; '
            f'$b isa book,   has isbn  "{isbn}"; '
            f'insert (author: $a, work: $b) isa wrote;'
        )
        tx.query(q).resolve()
        tx.commit()
    print(f"[ok] Linked author '{author_name}' → book '{isbn}'")


def list_books(driver, author_name=None):
    with driver.transaction(DB_NAME, TransactionType.READ) as tx:
        if author_name:
            q = (
                f'match '
                f'$a isa author, has name "{author_name}"; '
                f'(author: $a, work: $b) isa wrote; '
                f'$b has isbn $isbn, has title $title, has year $year; '
                f'fetch { "isbn": $isbn, "title": $title, "year": $year };'
            )
        else:
            q = (
                'match $b isa book, has isbn $isbn, has title $title, has year $year; '
                'fetch { "isbn": $isbn, "title": $title, "year": $year };'
            )
        answer = tx.query(q).resolve()
        docs = list(answer.as_concept_documents())

    if not docs:
        print("(no books found)")
        return

    print(f"\n{'ISBN':<18} {'Year':<6} Title")
    print("-" * 60)
    for doc in docs:
        isbn  = doc["isbn"]["value"]
        title = doc["title"]["value"]
        year  = doc["year"]["value"]
        print(f"{isbn:<18} {year:<6} {title}")
    print()


def list_authors(driver):
    with driver.transaction(DB_NAME, TransactionType.READ) as tx:
        q = (
            'match $a isa author, has name $name; '
            'fetch { "name": $name };'
        )
        answer = tx.query(q).resolve()
        docs = list(answer.as_concept_documents())

    if not docs:
        print("(no authors found)")
        return

    print("\nAuthors:")
    for doc in docs:
        print(f"  • {doc['name']['value']}")
    print()


def get_book(driver, isbn):
    with driver.transaction(DB_NAME, TransactionType.READ) as tx:
        q = (
            f'match $b isa book, has isbn "{isbn}", has $attr; '
            f'fetch {{ "attr": $attr }};'
        )
        answer = tx.query(q).resolve()
        attrs = list(answer.as_concept_documents())

        q2 = (
            f'match '
            f'$b isa book, has isbn "{isbn}"; '
            f'(author: $a, work: $b) isa wrote; '
            f'$a has name $name; '
            f'fetch {{ "name": $name }};'
        )
        answer2 = tx.query(q2).resolve()
        author_docs = list(answer2.as_concept_documents())

    if not attrs:
        print(f"No book found with ISBN {isbn}.")
        return

    print(f"\nBook — ISBN {isbn}")
    print("-" * 40)
    seen = set()
    for doc in attrs:
        a = doc["attr"]
        label = a.get("label", "?")
        value = a.get("value", "?")
        if label not in seen:
            seen.add(label)
            print(f"  {label:<14}: {value}")

    if author_docs:
        names = ", ".join(d["name"]["value"] for d in author_docs)
        print(f"  {'author(s)':<14}: {names}")
    print()


def delete_book(driver, isbn):
    with driver.transaction(DB_NAME, TransactionType.WRITE) as tx:
        q = (
            f'match '
            f'$b isa book, has isbn "{isbn}"; '
            f'$r isa wrote, links (work: $b); '
            f'delete $r isa wrote;'
        )
        tx.query(q).resolve()

        q2 = (
            f'match $b isa book, has isbn "{isbn}"; '
            f'delete $b isa book;'
        )
        tx.query(q2).resolve()
        tx.commit()
    print(f"[ok] Deleted book with ISBN {isbn}")


def delete_author(driver, name):
    with driver.transaction(DB_NAME, TransactionType.WRITE) as tx:
        q = (
            f'match '
            f'$a isa author, has name "{name}"; '
            f'$r isa wrote, links (author: $a); '
            f'delete $r isa wrote;'
        )
        tx.query(q).resolve()

        q2 = (
            f'match $a isa author, has name "{name}"; '
            f'delete $a isa author;'
        )
        tx.query(q2).resolve()
        tx.commit()
    print(f"[ok] Deleted author '{name}'")



def build_parser():
    p = argparse.ArgumentParser(
        prog="library",
        description="Minimal TypeDB library CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ab = sub.add_parser("add-book", help="Add a new book")
    ab.add_argument("isbn")
    ab.add_argument("title")
    ab.add_argument("year", type=int)
    ab.add_argument("genre", nargs="?", default=None)

    aa = sub.add_parser("add-author", help="Add a new author")
    aa.add_argument("name")
    aa.add_argument("birth_year", nargs="?", type=int, default=None)

    lk = sub.add_parser("link", help="Link an author to a book")
    lk.add_argument("author_name")
    lk.add_argument("isbn")

    lb = sub.add_parser("list-books", help="List all books (or filter by author)")
    lb.add_argument("--author", default=None, metavar="NAME")

    sub.add_parser("list-authors", help="List all authors")

    gb = sub.add_parser("get-book", help="Get details for a single book")
    gb.add_argument("isbn")

    db_ = sub.add_parser("delete-book", help="Delete a book by ISBN")
    db_.add_argument("isbn")

    da = sub.add_parser("delete-author", help="Delete an author by name")
    da.add_argument("name")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        with get_driver() as driver:
            ensure_db(driver)

            if args.command == "add-book":
                add_book(driver, args.isbn, args.title, args.year, args.genre)
            elif args.command == "add-author":
                add_author(driver, args.name, args.birth_year)
            elif args.command == "link":
                link(driver, args.author_name, args.isbn)
            elif args.command == "list-books":
                list_books(driver, author_name=args.author)
            elif args.command == "list-authors":
                list_authors(driver)
            elif args.command == "get-book":
                get_book(driver, args.isbn)
            elif args.command == "delete-book":
                delete_book(driver, args.isbn)
            elif args.command == "delete-author":
                delete_author(driver, args.name)

    except TypeDBDriverException as e:
        print(f"[error] TypeDB: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("[error] schema.tql not found — run from the project directory.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
