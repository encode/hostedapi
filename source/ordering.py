from dataclasses import dataclass
from starlette.datastructures import URL, QueryParams
import typing


@dataclass
class ColumnControl:
    id: str
    text: str
    url: URL = None
    is_forward_sorted: bool = False
    is_reverse_sorted: bool = False

    @property
    def is_sorted(self):
        return self.is_forward_sorted or self.is_reverse_sorted


def get_ordering(
    url: URL, allowed_column_ids: typing.Sequence[str]
) -> typing.Tuple[typing.Optional[str], bool]:
    """
    Determine a column ordering based on the URL query string.
    Returned as a tuple of (ordering, is_reverse).
    """
    query_params = QueryParams(url.query)

    ordering = query_params.get("order", default="")
    order_column = ordering.lstrip("-")
    order_reverse = ordering.startswith("-")
    if order_column not in allowed_column_ids:
        return None, False
    return order_column, order_reverse


def sort_by_ordering(
    items: list, column: typing.Optional[str], is_reverse: bool
) -> list:
    """
    Sort a data set by an ordering column.
    """
    if column is None:
        return items

    sort_key = lambda item: (getattr(item, column), item.pk)
    return sorted(items, key=sort_key, reverse=is_reverse)


def get_column_controls(
    url: URL, names: typing.List[str], column: typing.Optional[str], is_reverse: bool
) -> typing.List[ColumnControl]:
    controls = []
    for name in names:
        column_id = name.lower().replace(" ", "_")

        if column != column_id:
            # Column is not selected. Link URL to forward search.
            linked_url = url.include_query_params(order=column_id).remove_query_params(
                "page"
            )
        elif not is_reverse:
            # Column is selected as a forward search. Link URL to reverse search.
            linked_url = url.include_query_params(
                order="-" + column_id
            ).remove_query_params("page")
        else:
            # Column is selected as a reverse search. Link URL to remove search.
            linked_url = url.remove_query_params("order").remove_query_params("page")

        control = ColumnControl(
            id=column_id,
            text=name,
            url=linked_url,
            is_forward_sorted=column == column_id and not is_reverse,
            is_reverse_sorted=column == column_id and is_reverse,
        )
        controls.append(control)
    return controls
