from dataclasses import dataclass


@dataclass
class Book:
    item_id: str
    isbn: str
    category: str
    rating: str
    status: str
    tags: str
    registered_at: str
    title: str
    author: str
    publisher: str
    pub_year: str
    genre: str

    def search_text(self) -> str:
        return " ".join(
            part for part in (self.title, self.author, self.genre, self.tags) if part
        )
