def words(identifier: str) -> list[str]:
	return [word for word in identifier.split("_") if word]


def sentence(identifier: str) -> str:
	text = " ".join(words(identifier))
	return text[:1].upper() + text[1:]


def kebab(identifier: str) -> str:
	return "-".join(words(identifier))
