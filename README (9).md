# typedb-library

A minimal **TypeDB-backed book library** CLI written in Python.  
Demonstrates entities, attributes, relations, and all four CRUD operations against TypeDB 3.x.

---

## Domain model

```
author ──(wrote)──► book
```

| Concept   | Kind      | Owns / Relates                        |
|-----------|-----------|---------------------------------------|
| `book`    | entity    | `isbn` (key), `title`, `year`, `genre` |
| `author`  | entity    | `name` (key), `birth-year`            |
| `wrote`   | relation  | roles: `author`, `work`               |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **TypeDB ≥ 3.0** (Community Edition) | [Install guide](https://typedb.com/docs/home/install/ce/) — default port 1729 |
| **Python ≥ 3.9** | |
| **typedb-driver** Python package | `pip install typedb-driver` |

Start TypeDB locally before running the CLI:

```bash
typedb server
```

---

## Installation

```bash
git clone https://github.com/<your-username>/typedb-library.git
cd typedb-library
pip install typedb-driver
```

---

## Usage

Run every command from the project root (where `schema.tql` lives).  
The database and schema are created automatically on first run.

### Add a book
```bash
python library.py add-book 978-0-06-112008-4 "To Kill a Mockingbird" 1960 Fiction
python library.py add-book 978-0-7432-7356-5 "1984" 1949 Dystopia
```

### Add an author
```bash
python library.py add-author "Harper Lee" 1926
python library.py add-author "George Orwell" 1903
```

### Link an author to a book
```bash
python library.py link "Harper Lee" 978-0-06-112008-4
python library.py link "George Orwell" 978-0-7432-7356-5
```

### List all books
```bash
python library.py list-books
```

### List books by a specific author
```bash
python library.py list-books --author "George Orwell"
```

### Get details for a single book
```bash
python library.py get-book 978-0-06-112008-4
```

### List all authors
```bash
python library.py list-authors
```

### Delete a book (also removes its `wrote` relations)
```bash
python library.py delete-book 978-0-7432-7356-5
```

### Delete an author (also removes their `wrote` relations)
```bash
python library.py delete-author "George Orwell"
```

---

## Project layout

```
typedb-library/
├── library.py   # CLI application (Python, TypeDB Python driver)
├── schema.tql   # TypeQL schema definition
└── README.md
```

---

## TypeQL schema

```typeql
define

entity book,
    owns isbn @key,
    owns title,
    owns year,
    owns genre;

entity author,
    owns name @key,
    owns birth-year;

relation wrote,
    relates author,
    relates work;

book plays wrote:work;
author plays wrote:author;

attribute isbn,        value string;
attribute title,       value string;
attribute year,        value integer;
attribute genre,       value string;
attribute name,        value string;
attribute birth-year,  value integer;
```

---

## How it works

`library.py` connects to a local TypeDB server via the official Python driver.  
On first run it creates the `library` database and loads `schema.tql` as a schema transaction.  
Subsequent commands open write or read transactions as appropriate and execute TypeQL queries.

Key driver patterns used:

- **Schema transaction** — to define types once
- **Write transaction** — `insert` and `delete` queries, committed explicitly
- **Read transaction** — `match … fetch` queries returning concept documents
