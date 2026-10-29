import unittest
import tempfile
import os
import csv
from unittest.mock import patch

from main import (
    main,
    check_orders,
    inspect_csv,
    detect_column_types,
    looks_like_date,
    find_missing_values,
    find_duplicates,
    inspect_data_quality,
    suggest_duplicate_columns,
    find_invalid_numbers,
    explain_invalid_number,
    find_future_dates,
    explain_future_date,
    summarize_issues,
    find_structure_issues,
    repair_csv_structure,
)


class TestCheckOrders(unittest.TestCase):

    def test_clean_csv_has_no_issues(self):
        csv_content = (
            "order_id,customer_id,amount\n" "1001,201,49.99\n" "1002,202,120.00\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            total_rows, issues = check_orders(path)

            self.assertEqual(total_rows, 2)
            self.assertEqual(issues, [])
        finally:
            os.remove(path)

    def test_find_invalid_numbers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "employees.csv")

            with open(path, "w", newline="") as file:
                file.write(
                    "employee_id,name,salary\n"
                    "101,Alice,65000\n"
                    "102,Bob,unknown\n"
                    "103,Charlie,58000\n"
                )

            column_types = {
                "employee_id": "identifier",
                "name": "text",
                "salary": "number",
            }

            result = find_invalid_numbers(path, column_types)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["column"], "salary")
            self.assertEqual(result[0]["value"], "unknown")
            self.assertEqual(result[0]["row"], 3)

    def test_missing_customer_id(self):
        csv_content = "order_id,customer_id,amount\n" "1001,,49.99\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            total_rows, issues = check_orders(path)

            self.assertEqual(total_rows, 1)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["type"], "missing_customer_id")
        finally:
            os.remove(path)

    def test_duplicate_order_id(self):
        csv_content = (
            "order_id,customer_id,amount\n" "1001,201,49.99\n" "1001,202,25.00\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            total_rows, issues = check_orders(path)

            self.assertEqual(total_rows, 2)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["type"], "duplicate_order_id")
        finally:
            os.remove(path)

    def test_invalid_amount(self):
        csv_content = "order_id,customer_id,amount\n" "1001,201,abc\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            total_rows, issues = check_orders(path)

            self.assertEqual(total_rows, 1)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["type"], "invalid_amount")
        finally:
            os.remove(path)

    def test_missing_required_column(self):
        csv_content = "order_id,amount\n" "1001,49.99\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            with self.assertRaises(ValueError) as context:
                check_orders(path)

            self.assertIn("customer_id", str(context.exception))
        finally:
            os.remove(path)

    def test_inspect_csv_discovers_columns(self):
        csv_content = (
            "transaction_id,email,total_price\n" "T001,test@example.com,49.99\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            columns = inspect_csv(path)

            self.assertEqual(columns, ["transaction_id", "email", "total_price"])
        finally:
            os.remove(path)

    def test_detect_column_types(self):
        csv_content = (
            "customer,amount,category\n" "201,49.99,food\n" "202,120.00,books\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            column_types = detect_column_types(path)

            self.assertEqual(column_types["customer"], "number")
            self.assertEqual(column_types["amount"], "number")
            self.assertEqual(column_types["category"], "text")
        finally:
            os.remove(path)

    def test_looks_like_date(self):
        self.assertTrue(looks_like_date("2026-10-23"))
        self.assertTrue(looks_like_date("10/23/2026"))
        self.assertTrue(looks_like_date("2026-10-23 14:30:00"))

        self.assertFalse(looks_like_date("not-a-date"))
        self.assertFalse(looks_like_date("2026-13-40"))

    def test_detect_column_types_recognizes_dates(self):
        csv_content = (
            "record_id,created_at,amount\n"
            "R001,2026-10-20,49.99\n"
            "R002,2026-10-21,120.00\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            column_types = detect_column_types(path)

            self.assertEqual(column_types["record_id"], "identifier")
            self.assertEqual(column_types["created_at"], "date")
            self.assertEqual(column_types["amount"], "number")
        finally:
            os.remove(path)

    def test_find_missing_values(self):
        csv_content = (
            "customer_email,total_price\n" "alex@example.com,49.99\n" ",120.00\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            missing = find_missing_values(path)

            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0]["row"], 3)
            self.assertEqual(missing[0]["column"], "customer_email")
            self.assertEqual(missing[0]["type"], "missing_value")
        finally:
            os.remove(path)

    def test_find_duplicates_in_selected_column(self):
        csv_content = (
            "customer_email,city\n"
            "alex@example.com,Boston\n"
            "sam@example.com,New York\n"
            "alex@example.com,Chicago\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            duplicates = find_duplicates(path, "customer_email")

            self.assertEqual(len(duplicates), 1)
            self.assertEqual(duplicates[0]["row"], 4)
            self.assertEqual(duplicates[0]["column"], "customer_email")
            self.assertEqual(duplicates[0]["value"], "alex@example.com")
        finally:
            os.remove(path)

    def test_find_duplicates_with_unknown_column(self):
        csv_content = "customer_email,city\n" "alex@example.com,Boston\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            with self.assertRaises(ValueError) as context:
                find_duplicates(path, "transaction_id")

            self.assertIn("transaction_id", str(context.exception))
        finally:
            os.remove(path)

    def test_inspect_data_quality(self):
        csv_content = (
            "customer_email,total_price\n" "alex@example.com,49.99\n" ",120.00\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            report = inspect_data_quality(path)

            self.assertEqual(len(report["missing_values"]), 1)
            self.assertEqual(report["total_issues"], 1)
        finally:
            os.remove(path)

    def test_inspect_data_quality_counts_duplicates(self):
        csv_content = (
            "customer_email,city\n"
            "alex@example.com,Boston\n"
            "alex@example.com,Chicago\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write(csv_content)
            path = file.name

        try:
            report = inspect_data_quality(path, duplicate_columns=["customer_email"])

            self.assertEqual(len(report["duplicate_values"]), 1)
            self.assertEqual(report["total_issues"], 1)
            self.assertEqual(
                report["duplicate_values"][0]["column"],
                "customer_email",
            )
        finally:
            os.remove(path)

    def test_suggest_duplicate_columns(self):
        column_types = {
            "order_id": "identifier",
            "customer_id": "identifier",
            "amount": "number",
            "created_at": "date",
        }

        result = suggest_duplicate_columns(column_types)

        self.assertEqual(result, ["order_id"])

    def test_explain_invalid_number(self):
        issue = {
            "row": 3,
            "column": "salary",
            "value": "unknown",
            "type": "invalid_number",
        }

        result = explain_invalid_number(issue)

        self.assertIn("salary", result)
        self.assertIn("unknown", result)
        self.assertIn("row 3", result)
        self.assertIn("valid number", result)

    def test_explain_future_date(self):
        issue = {
            "row": 2,
            "column": "hire_date",
            "value": "2035-01-15",
            "type": "future_date",
        }

        result = explain_future_date(issue)

        self.assertIn("hire_date", result)
        self.assertIn("2035-01-15", result)
        self.assertIn("row 2", result)
        self.assertIn("Check whether this date was entered correctly", result)

    def test_find_future_dates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "employees.csv")

            with open(path, "w", newline="") as file:
                file.write("employee_id,name,hire_date\n" "101,Alice,2035-01-15\n")

            column_types = {
                "employee_id": "identifier",
                "name": "text",
                "hire_date": "date",
            }

            result = find_future_dates(path, column_types)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["column"], "hire_date")
            self.assertEqual(result[0]["value"], "2035-01-15")
            self.assertEqual(result[0]["type"], "future_date")

    def test_past_date_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "employees.csv")

            with open(path, "w", newline="") as file:
                file.write("employee_id,name,hire_date\n" "101,Alice,2020-01-15\n")

            column_types = {
                "employee_id": "identifier",
                "name": "text",
                "hire_date": "date",
            }

            result = find_future_dates(path, column_types)

            self.assertEqual(result, [])

    def test_negative_salary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "employees.csv")

            with open(path, "w", newline="") as file:
                file.write(
                    "employee_id,name,salary\n" "101,Alice,65000\n" "102,Bob,-72000\n"
                )

            column_types = {
                "employee_id": "identifier",
                "name": "text",
                "salary": "number",
            }

            result = find_invalid_numbers(path, column_types)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["type"], "negative_salary")
            self.assertEqual(result[0]["value"], "-72000")

    def test_summarize_issues(self):
        missing_values = [{"column": "name"}]
        duplicate_values = [{"column": "employee_id"}]
        invalid_numbers = [{"type": "invalid_number"}]
        future_dates = [{"column": "hire_date"}]

        summary = summarize_issues(
            missing_values,
            duplicate_values,
            invalid_numbers,
            future_dates,
        )

        self.assertEqual(summary["missing_values"], 1)
        self.assertEqual(summary["duplicate_values"], 1)
        self.assertEqual(summary["invalid_numbers"], 1)
        self.assertEqual(summary["negative_salaries"], 0)
        self.assertEqual(summary["future_dates"], 1)
        self.assertEqual(summary["total_issues"], 4)

    def test_main_handles_missing_file(self):
        with patch("builtins.input", return_value="missing_file.csv"):
            with patch("builtins.print") as mock_print:
                main()

        mock_print.assert_any_call(
            "Error: File not found. Please check the path and try again."
        )

    def test_main_rejects_non_csv_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as temp_file:
            with patch("builtins.input", return_value=temp_file.name):
                with patch("builtins.print") as mock_print:
                    main()

        mock_print.assert_any_call("Error: Please provide a CSV file.")

    def test_inspect_csv_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", newline="", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            with self.assertRaisesRegex(ValueError, "empty or has no headers"):
                inspect_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_inspect_csv_headers_only(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write("employee_id,name,salary\n")
            temp_path = temp_file.name

        try:
            with self.assertRaisesRegex(ValueError, "no data rows"):
                inspect_csv(temp_path)
        finally:
            os.remove(temp_path)

    def test_find_structure_issues(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", newline="", delete=False
        ) as temp_file:
            temp_file.write(
                "employee_id,name,salary\n"
                "101,Jude,5000\n"
                "102,Sara\n"
                "103,Ali,6000,Extra\n"
            )
            temp_path = temp_file.name

        try:
            issues = find_structure_issues(temp_path)

            self.assertEqual(len(issues), 2)
            self.assertEqual(issues[0]["type"], "missing_fields")
            self.assertEqual(issues[0]["row"], 3)
            self.assertEqual(issues[1]["type"], "extra_fields")
            self.assertEqual(issues[1]["row"], 4)
            self.assertEqual(issues[1]["extra_values"], ["Extra"])
        finally:
            os.remove(temp_path)

    def test_repair_csv_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = os.path.join(temp_dir, "employees.csv")

            with open(csv_path, "w", newline="") as file:
                file.write(
                    "employee_id,name,salary\n"
                    "101,Jude,5000\n"
                    "102,Sara\n"
                    "103,Ali,6000,Extra\n"
                )
            with open(csv_path, "r") as file:
                original_contents = file.read()
            repaired_path, report_path = repair_csv_structure(csv_path)

            with open(repaired_path, newline="") as file:
                rows = list(csv.reader(file))

            with open(report_path, newline="") as file:
                report = list(csv.reader(file))

            self.assertEqual(len(rows[2]), 3)
            self.assertEqual(rows[2], ["102", "Sara", ""])
            self.assertEqual(rows[3], ["103", "Ali", "6000"])
            self.assertEqual(report[1], ["4", "Extra"])

            with open(csv_path, "r") as file:
                self.assertEqual(file.read(), original_contents)


if __name__ == "__main__":
    unittest.main()
