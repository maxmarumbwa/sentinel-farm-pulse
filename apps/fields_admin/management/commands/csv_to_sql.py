import csv
import os


def csv_to_insert_sql(csv_file, table_name, output_file=None):
    """
    Convert a CSV file into PostgreSQL INSERT statements.

    Parameters
    ----------
    csv_file : str
        Path to the CSV file.
    table_name : str
        PostgreSQL table name.
    output_file : str, optional
        Output SQL file. If None, uses CSV filename with .sql extension.
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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    from django.conf import settings
    import os
    csv_path = os.path.join(settings.BASE_DIR,"static","csv","zwe_adm1.csv")
    
    csv_to_insert_sql(
        csv_file=csv_path,
        table_name="fields_admin_admin1"
    )