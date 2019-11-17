from collections import Counter
from slugify import slugify
import typesystem


def normalize_length(row, length):
    row_length = len(row)
    if row_length > length:
        return row[:length]
    elif row_length < length:
        return row + ["" for idx in range(length - row_length)]
    return row


def normalize_table(rows):
    # Strip all leading/trailing whitespace.
    rows = [[item.strip() for item in row] for row in rows]

    # Remove any rows that only have blank values.
    rows = [row for row in rows if any(row)]

    # Normalize so that all rows have the same length.
    # To determine the best column length, we pick the most common case.
    length = len(rows[0])
    length_counter = Counter([len(row) for row in rows])
    most_common_lengths = length_counter.most_common()
    if len(most_common_lengths) > 1:
        length, count = most_common_lengths[0]
        rows = [normalize_length(row, length) for row in rows]

    # Strip out any columns that only have blank values.
    blank_columns = set([idx for idx in range(length)])
    for row in rows:
        for idx, item in enumerate(row):
            # If a column has a non-empty value, then remove it from the
            # 'blank_columns' set.
            if idx in blank_columns and item:
                blank_columns.remove(idx)
                if not blank_columns:
                    # We can skip out early if there's nothing left in our
                    # blank columns set.
                    break

    if blank_columns:
        rows = [
            [item for idx, item in enumerate(row) if idx not in blank_columns]
            for row in rows
        ]

    # Start from the first completely populated row.
    starting_idx = 0
    for idx, row in enumerate(rows):
        if all([item for item in row]):
            starting_idx = idx
            break

    return rows[starting_idx:]


def determine_column_identities(rows):
    return [slugify(name, to_lower=True) for name in rows[0]]


def determine_column_types(rows):
    identities = determine_column_identities(rows)

    candidate_types = [("integer", typesystem.Integer(allow_null=True))]
    column_types = []
    fields = {}
    for idx, identity in enumerate(identities):
        column = [row[idx] for row in rows[1:] if row[idx]]

        for name, candidate in candidate_types:
            list_validator = typesystem.Array(items=candidate)
            validated, errors = list_validator.validate_or_error(column)
            if not errors:
                column_types.append(name)
                fields[identity] = candidate
                break
        else:
            column_types.append("string")
            fields[identity] = candidate = typesystem.String(allow_blank=True)

    print(column_types, rows)
    schema = type("Schema", (typesystem.Schema,), fields)
    return column_types, schema
