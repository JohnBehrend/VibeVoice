import argparse
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def epub2html(epub_path):
    book = epub.read_epub(epub_path)
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            txt = BeautifulSoup(item.get_content()).get_text(separator=" ", strip=False)
            if txt:
              chapters.append(txt)
    return chapters
if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Dump head of an ebook to a text file.")
  parser.add_argument("-ebook", metavar="example.epbu", help="Ebook to dump.")
  args = parser.parse_args()
  if args.ebook is None:
    chapters = epub2html("c:/Users/j3p3/Documents/Repos/VibeVoice/Books/WoT3TDR.epub")
  else:
    chapters = epub2html(args.ebook)
  print(chapters[1][:948])