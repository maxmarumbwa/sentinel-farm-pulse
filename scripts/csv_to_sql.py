import csv
import os


def csv_to_insert_sql(csv_file, table_name, output_file=None):
    """
    Convert a CSV file into PostgreSQL INSERT statements.
    """

    if output_file is None:
        output_file = os.path.splitext(csv_file)[0] + ".sql"

    with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        columns = reader.fieldnames

        if not columns:
            raise Exception("CSV contains no columns.")

        sql = []

        sql.append(
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES\n"
        )

        values = []

        for row in reader:
            row_values = []

            for col in columns:
                value = row[col]

                if value is None or value == "":
                    row_values.append("NULL")
                else:
                    value = value.replace("'", "''")
                    row_values.append(f"'{value}'")

            values.append("(" + ", ".join(row_values) + ")")

        sql.append(",\n".join(values))
        sql.append(";")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(sql))

    print(f"SQL file written to: {output_file}")


if __name__ == "__main__":

    # Folder containing this script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

    # Project root (parent of scripts/)
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

    # Path to CSV
    csv_path = os.path.join(
        PROJECT_ROOT,
        "static",
        "csv",
        "zwe_adm3.csv"
    )

    csv_to_insert_sql(
        csv_file=csv_path,
        table_name="fields_admin_admin3"
    )