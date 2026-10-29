import csv
import os
from datetime import datetime

from explain import print_report


def check_orders(path):
    """Read the CSV and return the number of rows and detected issues."""

    issues = []
    seen_order_ids = set()
    total_rows = 0

    with open(path, newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {"order_id", "customer_id", "amount"}
        actual_columns = reader.fieldnames or []

        if not required_columns.issubset(actual_columns):
            missing_columns = required_columns - set(actual_columns)
            raise ValueError(f"Missing required columns: {missing_columns}")

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1

            # Check whether the order amount is valid
            amount = row.get("amount", "").strip()

            try:
                amount_value = float(amount)

                if amount_value < 0:
                    issues.append(
                        {
                            "type": "invalid_amount",
                            "row": row_number,
                            "order_id": row.get("order_id", ""),
                        }
                    )

            except ValueError:
                issues.append(
                    {
                        "type": "invalid_amount",
                        "row": row_number,
                        "order_id": row.get("order_id", ""),
                    }
                )

            # Check whether the customer ID is missing
            if not row.get("customer_id", "").strip():
                issues.append(
                    {
                        "type": "missing_customer_id",
                        "row": row_number,
                        "order_id": row.get("order_id", ""),
                    }
                )

            order_id = row.get("order_id", "").strip()

            # Check whether the order ID is missing
            if not order_id:
                issues.append(
                    {
                        "type": "missing_order_id",
                        "row": row_number,
                        "order_id": "",
                    }
                )

            # Check whether the order ID has appeared before
            if order_id and order_id in seen_order_ids:
                issues.append(
                    {
                        "type": "duplicate_order_id",
                        "row": row_number,
                        "order_id": order_id,
                    }
                )
            elif order_id:
                seen_order_ids.add(order_id)

    return total_rows, issues


def inspect_csv(path):
    """Return the column names found in a CSV file."""

    with open(path, newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []

        if not columns:
            raise ValueError("The CSV file is empty or has no headers.")

        rows = list(reader)

        if not rows:
            raise ValueError("The CSV file contains headers but no data rows.")

    return columns


def find_structure_issues(path):
    """Find CSV rows with missing or extra fields."""

    issues = []

    with open(path, newline="") as file:
        reader = csv.reader(file)
        headers = next(reader, None)

        if headers is None:
            return issues

        expected_fields = len(headers)

        for row_number, row in enumerate(reader, start=2):
            if len(row) < expected_fields:
                issues.append(
                    {
                        "row": row_number,
                        "type": "missing_fields",
                        "expected": expected_fields,
                        "actual": len(row),
                    }
                )
            elif len(row) > expected_fields:
                issues.append(
                    {
                        "row": row_number,
                        "type": "extra_fields",
                        "expected": expected_fields,
                        "actual": len(row),
                        "extra_values": row[expected_fields:],
                    }
                )

    return issues


def repair_csv_structure(path):
    """Create a cleaned CSV and a report of extra values."""

    repaired_path = path.rsplit(".", 1)[0] + "_repaired.csv"
    report_path = path.rsplit(".", 1)[0] + "_repair_report.csv"

    extra_values = []

    with open(path, newline="") as file:
        reader = csv.reader(file)
        headers = next(reader, None)

        if headers is None:
            return None, None

        repaired_rows = []

        for row_number, row in enumerate(reader, start=2):
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))

            elif len(row) > len(headers):
                extra_values.append(
                    {
                        "row": row_number,
                        "extra_values": row[len(headers) :],
                    }
                )
                row = row[: len(headers)]

            repaired_rows.append(row)

    with open(repaired_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(repaired_rows)

    with open(report_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["row", "extra_value_1", "extra_value_2"])

        for issue in extra_values:
            writer.writerow(
                [
                    issue["row"],
                    *issue["extra_values"],
                ]
            )

    return repaired_path, report_path


def detect_column_types(path):
    """Guess the data type of each column from its values."""

    with open(path, newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        rows = list(reader)

    column_types = {}

    for column in columns:

        values = [
            (row.get(column) or "").strip()
            for row in rows
            if (row.get(column) or "").strip()
        ]

        column_name = column.lower()

        if not values:
            column_types[column] = "empty"

        elif "id" in column_name:
            column_types[column] = "identifier"

        elif all(looks_like_date(value) for value in values):
            column_types[column] = "date"

        else:
            numeric_values = []

            for value in values:
                try:
                    float(value)
                    numeric_values.append(True)
                except ValueError:
                    numeric_values.append(False)

            if any(numeric_values):
                column_types[column] = "number"
            else:
                column_types[column] = "text"

    return column_types


def suggest_duplicate_columns(column_types):
    """Suggest columns likely to contain unique record IDs."""

    unique_id_keywords = (
        "order_id",
        "transaction_id",
        "invoice_id",
        "order_number",
        "transaction_number",
        "invoice_number",
    )

    return [
        column
        for column, data_type in column_types.items()
        if data_type == "identifier" and column.lower() in unique_id_keywords
    ]


def looks_like_date(value):
    """Check whether a value matches a supported date format."""

    date_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S",
    ]

    for date_format in date_formats:
        try:
            datetime.strptime(value, date_format)
            return True
        except ValueError:
            continue

    return False


def find_future_dates(path, column_types):
    """Find dates that occur in the future."""

    future_dates = []

    with open(path, newline="") as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            for column, data_type in column_types.items():
                if data_type != "date":
                    continue

                value = (row.get(column) or "").strip()

                if not value:
                    continue

                date_formats = [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%Y-%m-%d %H:%M:%S",
                ]

                for date_format in date_formats:
                    try:
                        date_value = datetime.strptime(value, date_format).date()

                        if date_value > datetime.today().date():
                            future_dates.append(
                                {
                                    "row": row_number,
                                    "column": column,
                                    "value": value,
                                    "type": "future_date",
                                }
                            )

                        break
                    except ValueError:
                        continue

    return future_dates


def explain_future_date(issue):
    """Explain why a future date might be suspicious."""

    column = issue["column"]
    value = issue["value"]
    row = issue["row"]

    return (
        f"Possible data-quality issue: '{column}' contains the future "
        f"date '{value}' on CSV row {row}. "
        "Check whether this date was entered correctly."
    )


def find_missing_values(path):
    """Find missing values in every column of a CSV file."""

    missing = []

    with open(path, newline="") as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            for column, value in row.items():
                if column is not None and (value is None or not str(value).strip()):
                    missing.append(
                        {
                            "row": row_number,
                            "column": column,
                            "type": "missing_value",
                        }
                    )

    return missing


def find_invalid_numbers(path, column_types):
    """Find values that should be numbers but cannot be converted."""

    invalid_values = []

    with open(path, newline="") as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            for column, data_type in column_types.items():
                if data_type != "number":
                    continue

                value = (row.get(column) or "").strip()

                if not value:
                    continue

                try:
                    number = float(value)

                    if number < 0 and "salary" in column.lower():
                        invalid_values.append(
                            {
                                "row": row_number,
                                "column": column,
                                "value": value,
                                "type": "negative_salary",
                            }
                        )

                except ValueError:
                    invalid_values.append(
                        {
                            "row": row_number,
                            "column": column,
                            "value": value,
                            "type": "invalid_number",
                        }
                    )

    return invalid_values


def explain_invalid_number(issue):
    """Explain an invalid numeric value in plain English."""

    column = issue["column"]
    value = issue["value"]
    row = issue["row"]

    if issue["type"] == "negative_salary":
        return (
            f"Possible data-quality issue: '{column}' has a negative "
            f"value of {value} on CSV row {row}. "
            "Check whether this value is correct."
        )
    return (
        f"Invalid value in '{column}': '{value}' is not a valid number. "
        f"This value appears on CSV row {row}. "
        f"Replace it with a valid number, or leave it blank "
        f"if the value is unknown."
    )


def find_duplicates(path, column):
    """Find repeated non-empty values in a selected column."""

    duplicates = []
    seen_values = set()

    with open(path, newline="") as file:
        reader = csv.DictReader(file)

        if column not in (reader.fieldnames or []):
            raise ValueError(f"Column not found: {column}")

        for row_number, row in enumerate(reader, start=2):
            value = (row.get(column) or "").strip()

            if value and value in seen_values:
                duplicates.append(
                    {
                        "row": row_number,
                        "column": column,
                        "value": value,
                        "type": "duplicate_value",
                    }
                )
            elif value:
                seen_values.add(value)

    return duplicates


def inspect_data_quality(path, duplicate_columns=None):
    """Collect general-purpose data quality issues."""

    missing_values = find_missing_values(path)
    duplicate_issues = []

    for column in duplicate_columns or []:
        duplicate_issues.extend(find_duplicates(path, column))

    total_issues = len(missing_values) + len(duplicate_issues)

    return {
        "missing_values": missing_values,
        "duplicate_values": duplicate_issues,
        "total_issues": total_issues,
    }


def summarize_issues(missing_values, duplicate_values, invalid_numbers, future_dates):
    """Count data-quality issues by category."""

    negative_salaries = [
        issue for issue in invalid_numbers if issue["type"] == "negative_salary"
    ]

    actual_invalid_numbers = len(invalid_numbers) - len(negative_salaries)

    total_issues = (
        len(missing_values)
        + len(duplicate_values)
        + actual_invalid_numbers
        + len(negative_salaries)
        + len(future_dates)
    )

    return {
        "missing_values": len(missing_values),
        "duplicate_values": len(duplicate_values),
        "invalid_numbers": actual_invalid_numbers,
        "negative_salaries": len(negative_salaries),
        "future_dates": len(future_dates),
        "total_issues": total_issues,
    }


def main():
    """Run the checks and let the user verify corrections."""

    csv_path = input("Enter the path to your CSV file: ")
    if not os.path.exists(csv_path):
        print("Error: File not found. Please check the path and try again.")
        return
    if not csv_path.lower().endswith(".csv"):
        print("Error: Please provide a CSV file.")
        return

    try:
        # Inspect the CSV structure
        columns = inspect_csv(csv_path)

        structure_issues = find_structure_issues(csv_path)

        print("\n--- CSV Structure Check ---")

        if not structure_issues:
            print("No row-structure issues found.")
        else:
            print(f"Structure issues found: {len(structure_issues)}")
            for issue in structure_issues:
                print(
                    f"CSV row {issue['row']}: "
                    f"{issue['type'].replace('_', ' ')}. "
                    f"Expected {issue['expected']} fields, "
                    f"found {issue['actual']}."
                )

            repair_choice = (
                input("\nWould you like to repair the CSV structure? (y/n): ")
                .strip()
                .lower()
            )

            if repair_choice == "y":
                repaired_path, report_path = repair_csv_structure(csv_path)

                if repaired_path:
                    print(f"Repaired CSV saved to: {repaired_path}")
                    print(f"Extra values report saved to: {report_path}")

                    run_again = (
                        input("Would you like to check the repaired CSV now? (y/n): ")
                        .strip()
                        .lower()
                    )

                    if run_again in ("y", "yes"):
                        csv_path = repaired_path
                    else:
                        return
                else:
                    return

        print("\n--- CSV structure ---")
        print(f"Columns found ({len(columns)}): {', '.join(columns)}")

        # Detect column types
        column_types = detect_column_types(csv_path)

        print("\n--- Detected column types ---")
        for column, data_type in column_types.items():
            print(f"{column}: {data_type}")

        # Suggest columns for duplicate checking
        suggested_columns = suggest_duplicate_columns(column_types)

        quality_report = inspect_data_quality(
            csv_path,
            duplicate_columns=suggested_columns,
        )

        # Display duplicate results
        duplicate_values = quality_report["duplicate_values"]

        print("\n--- Duplicate-value check ---")
        print(f"Duplicate values found: {len(duplicate_values)}")

        for issue in duplicate_values:
            print(
                f"CSV row {issue['row']}, "
                f"column '{issue['column']}': "
                f"duplicate value '{issue['value']}'"
            )

        # Display missing-value results
        missing_values = quality_report["missing_values"]

        print("\n--- Missing-value check ---")
        print(f"Missing values found: {len(missing_values)}")
        print(f"Total generic issues: {quality_report['total_issues']}")

        for issue in missing_values:
            print(
                f"CSV row {issue['row']}, " f"column '{issue['column']}': missing value"
            )

        invalid_numbers = find_invalid_numbers(csv_path, column_types)

        future_dates = find_future_dates(csv_path, column_types)

        print("\n--- Future-date check ---")
        print(f"Future dates found: {len(future_dates)}")

        for issue in future_dates:
            print(f"\n{explain_future_date(issue)}")

        print("\n--- Invalid-number check ---")
        print(f"Invalid numbers found: {len(invalid_numbers)}")

        for issue in invalid_numbers:
            print(f"\n{explain_invalid_number(issue)}")

        summary = summarize_issues(
            missing_values,
            duplicate_values,
            invalid_numbers,
            future_dates,
        )

        print("\n--- Data Quality Summary ---")
        print(f"Missing values: {summary['missing_values']}")
        print(f"Duplicate values: {summary['duplicate_values']}")
        print(f"Invalid numbers: {summary['invalid_numbers']}")
        print(f"Negative salaries: {summary['negative_salaries']}")
        print(f"Future dates: {summary['future_dates']}")
        print(f"Total issues: {summary['total_issues']}")

        # Run order-specific checks only for order datasets
        required_columns = {"order_id", "customer_id", "amount"}

        if required_columns.issubset(columns):
            total_rows, issues = check_orders(csv_path)
            print_report(total_rows, issues)

            # Offer a recheck only when order issues exist
            if issues:
                input("\nFix the CSV, save it, " "then press Enter to re-check...")

                new_total, new_issues = check_orders(csv_path)

                print("\n--- Re-check results ---")
                print(f"Issues before: {len(issues)}")
                print(f"Issues now: {len(new_issues)}")

                print_report(new_total, new_issues)

                if not new_issues:
                    print(
                        "\nAll order checks passed. "
                        "No order-specific issues were detected."
                    )
        else:
            print("\n--- Order-specific checks ---")
            print("Skipped: this CSV does not contain " "the required order columns.")

    except FileNotFoundError:
        print(f"Error: Could not find '{csv_path}'. Check the file path.")

    except ValueError as error:
        print(f"Data structure error: {error}")

    except (KeyError, csv.Error) as error:
        print(f"Error reading the CSV file: {error}")


if __name__ == "__main__":
    main()
