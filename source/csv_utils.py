from collections import Counter


def normalize_length(row, length):
    row_length = len(row)
    if row_length > length:
        return row[:length]
    elif row_length < length:
        return row + ["" for idx in range(length - row_length)]
    return row


def normalize_table(rows):
    # Strip out any rows that only have blank values.
    rows = [row for row in rows if any((item.strip() for item in row))]

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
            if idx in blank_columns and item.strip():
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
    return rows
