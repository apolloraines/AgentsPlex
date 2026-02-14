This project is designed to help you learn how to code.
Make sure to receive feedback from your peers.
"""
        },
        {
            "title": "Improve performance of data processing",
            "description": "Refactored the data processing function to reduce time complexity.",
            "code": """
def process_data(data):
    # O(n^2) complexity
    results = []
    for i in data:
        for j in data:
            if i == j:
                results.append(i)
    return results
"""
        },
        {
            "title": "Add missing error handling",
            "description": "Added error handling to prevent crashes when input is invalid.",
            "code": """
def divide(x, y):
    try:
        return x / y
    except ZeroDivisionError:
        return 'Cannot divide by zero'
"""
        },
        {
            "title": "Security fix: SQL Injection vulnerability",
            "description": "Used parameterized queries to prevent SQL injection.",
            "code": """
import sqlite3

def get_user_data(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
"""
        },
        {
            "title": "Introduce feature: User registration",
            "description": "Implemented a new user registration feature with validation.",
            "code": """
def register_user(username, password):
    if len(username) < 3 or len(password) < 6:
        return 'Invalid username or password'
    # Assume users is a predefined list
    users.append({'username': username, 'password': password})
    return 'User registered successfully'
"""
        },
        {
            "title": "Bug fix: Incorrect calculation in sum function",
            "description": "Fixed the bug where the sum function was returning the wrong total.",
            "code": """
def sum_numbers(numbers):
    total = 0
    for number in numbers:
        total += number
    return total
"""
        },
        {
            "title": "Enhancement: Logging added",
            "description": "Added logging to track function calls and errors.",
            "code": """
import logging

logging.basicConfig(level=logging.INFO)

def process_numbers(numbers):
    logging.info('Processing numbers')
    for number in numbers:
        if number < 0:
            logging.error('Negative number encountered: %s', number)
        else:
            print(number)
"""
        },
        {
            "title": "Deprecated method removal",
            "description": "Removed deprecated method due to compatibility issues.",
            "code": """
def old_method():
    raise NotImplementedError("This method is deprecated and should not be used.")
"""
        },
        {
            "title": "Test case for login functionality",
            "description": "Added test case for the login functionality.",
            "code": """
def test_login():
    assert login('validUser', 'validPassword') == 'Login success'
    assert login('invalidUser', 'invalidPassword') == 'Login failed'
"""
        }
    ]
```