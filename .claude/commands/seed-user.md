---
description: Create a single dummy user in the database
allowed-tools: Read, Bash(python3:*)
---

Read database/db.py to understand the users table
schema and the get_db() helper.
Then write and run a Python script using Bash that:

1. Generates a realistic random Indian user using your own knowledge of common Indian names across regions:

   * Name: a realistic Indian first + last name
   * Email: derived from the name with a random 2–3 digit number suffix (e.g. [rahul,sharma91@gmail.com](mailto:rahul.sharma91@gmail.com))
   * Password: "password123" hashed with werkzeug's generate_password_hash
   * created_at: current datetime

2. Checks if the generated email already exists in the users table. If it does, regenerate until unique.

3. Inserts the user into the database using the same get_db() pattern found in db.py.

4. Prints:

   * generated name
   * generated email
   * inserted user id
<!-- 
5. After insertion, query the database and print the inserted row to verify persistence.

Requirements:

* Use sqlite3 only
* Use parameterized SQL queries
* Reuse the existing schema and helper functions
* Keep the script standalone and runnable from project root
* Do not modify any existing routes or templates
* Follow the coding style already used in database/db.py

git commit -m "database: add random indian user seed script" -->
