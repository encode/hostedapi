from starlette.exceptions import HTTPException


class MediaType:
    """
    Holds a media type, such as:

    * "text/html;q=0.9"
    * "text/html"
    * "text/*"
    * "*/*"
    """

    def __init__(self, media_type):
        full_type, _, self.params = media_type.partition(";")
        self.main_type, _, self.sub_type = full_type.partition("/")

        self.main_type = self.main_type.strip()
        self.sub_type = self.sub_type.strip()
        self.params = self.params.strip()

    @property
    def precedence(self):
        """
        Return a precedence level from 0-2 for the media type given how specific it is.
        """
        if self.main_type == "*":
            return 0
        elif self.sub_type == "*":
            return 1
        return 2

    def matches(self, other):
        if self.main_type == "*" and self.sub_type == "*":
            return True
        if self.main_type == other.main_type and self.sub_type == "*":
            return True
        if self.main_type == other.main_type and self.sub_type == other.sub_type:
            return True
        return False

    def __str__(self):
        if self.params:
            return f"{self.main_type}/{self.sub_type}; {self.params}"
        return f"{self.main_type}/{self.sub_type}"


def negotiate(accept_header, media_types):
    requested_types = [MediaType(token) for token in accept_header.split(",")]
    acceptable_types = [MediaType(token) for token in media_types]

    requested_types_by_precedence = (
        [token for token in requested_types if token.precedence == 2],
        [token for token in requested_types if token.precedence == 1],
        [token for token in requested_types if token.precedence == 0],
    )
    for requested_type_set in requested_types_by_precedence:
        for acceptable_type in acceptable_types:
            for requested_type in requested_type_set:
                if requested_type.matches(acceptable_type):
                    return str(acceptable_type)
    raise HTTPException(status_code=406)
