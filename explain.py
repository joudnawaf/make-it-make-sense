# Store plain-English explanations for each type of data quality issue
EXPLANATIONS = {
    "missing_customer_id": {
        "title": "Missing customer ID",
        "what": "An order has no customer ID filled in.",
        "why": "We can't connect this order to a customer, so customer-level reports may be incomplete.",
        "fix": "Check the original order record and restore the correct customer ID.",
    },
    "duplicate_order_id": {
        "title": "Duplicate order ID",
        "what": "The same order ID appears more than once.",
        "why": "An order may be counted more than once, which can inflate order totals and revenue.",
        "fix": "Compare the records with the original source before removing or correcting either record.",
    },
    "invalid_amount": {
    "title": "Invalid order amount",
    "what": "An order amount is missing, is not a valid number, or is negative.",
    "why": "Invalid amounts can make revenue totals and financial reports inaccurate.",
    "fix": "Check the original order record and confirm the correct amount before updating it.",
},
"missing_order_id": {
    "title": "Missing order ID",
    "what": "An order has no order ID filled in.",
    "why": "Without an order ID, we can't reliably identify or track the order.",
    "fix": "Check the original order record and restore the correct order ID.",
},
}


def print_report(total_rows, issues):
    """Display the data quality score, status, and explanations."""

    # Count each affected row only once
    rows_with_issues = len({issue["row"] for issue in issues})

    # Calculate the percentage of rows without detected issues
    if total_rows > 0:
        score = max(0, 100 - (rows_with_issues / total_rows * 100))
    else:
        score = 0

    # Set the status based on whether any issues were found
    status = "WARNING" if issues else "HEALTHY"

    print(f"\nRows processed: {total_rows}")
    print(f"Status: {status}")
    print(f"Data quality score: {score:.2f}/100")
    print(f"Rows with issues: {rows_with_issues}")
    print(f"Total issues found: {len(issues)}")
    print("\n--- Issue summary ---")

    for issue_type, info in EXPLANATIONS.items():
     count = sum(1 for issue in issues if issue["type"] == issue_type)
     print(f"{info['title']}: {count}")

  
    # Display an explanation for each type of issue found
    for issue_type, info in EXPLANATIONS.items():
        matches = [
            issue for issue in issues
            if issue["type"] == issue_type
        ]

        if matches:
            print(f"\n--- {info['title']} ({len(matches)} found) ---")

            for issue in matches:
                print(f"CSV row: {issue['row']}")
                print(f"Order ID: {issue['order_id']}")

            print(f"What went wrong: {info['what']}")
            print(f"Why it matters:  {info['why']}")
            print(f"What to do:      {info['fix']}")
