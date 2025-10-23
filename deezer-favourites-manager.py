import os
import sys
import requests
from bs4 import BeautifulSoup
from tkinter import *
from tkinter import ttk, messagebox

HTMLFILENAME = "deezer-favourites.html"

# Base HTML template for the file
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Deezer Favourites</title>
<style>
  body {
  font-family: Arial, sans-serif;
  background: #fafafa;
  color: #333;
  margin: 0;
  padding: 1rem;
  line-height: 1.5;
  font-size: 18px;
  
}

h1 {
  text-align: left;
  color: #222;
  font-size: 2rem;
  margin-bottom: 1.2rem;
}

.category {
  background: #fff;
  margin-bottom: 6rem;
  border-radius: 10px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  padding: 1rem;
}

.category h2 {
  font-size: 2rem;
  margin: 0 0 0.8rem 0;
  color: #0066cc;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.4rem;
}

.link-item {
  margin-bottom: 0.7rem;
}

a {
  color: #0078d7;
  text-decoration: none;
  word-wrap: break-word;
  font-size: 2rem;
}

a:hover {
  text-decoration: underline;
}
</style>
</head>
<body>
<h1>Deezer Favourites</h1>
</body>
</html>
"""

def ensurehtmlfile():
    """Ensures the HTML file exists with the base structure."""
    if not os.path.exists(HTMLFILENAME):
        with open(HTMLFILENAME, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE)

def load_data_from_html():
    """Reads the HTML file and returns structured data and category names."""
    link_data = []
    category_names = set()
    try:
        with open(HTMLFILENAME, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except FileNotFoundError:
        return link_data, list(category_names)

    # Iterate through all category divs
    for category_div in soup.find_all("div", class_="category"):
        h2 = category_div.find("h2")
        if not h2:
            continue
        category_name = h2.text.strip()
        category_names.add(category_name)

        # Iterate through all links in the category
        for link_item in category_div.find_all("div", class_="link-item"):
            link_tag = link_item.find("a")
            if not link_tag or not link_tag.string:
                continue

            # Text is expected to be "Artist - Album"
            text_parts = link_tag.string.split(" - ", 1)
            if len(text_parts) == 2:
                artist = text_parts[0].strip()
                album = text_parts[1].strip()
                url = link_tag.get("href")

                if url:
                    link_data.append({
                        'category': category_name,
                        'artist': artist,
                        'album': album,
                        'url': url
                    })

    return link_data, sorted(list(category_names))

def write_data_to_html(link_data):
    """Sorts the data and rewrites the entire HTML file."""
    
    # 1. Sort the data: 
    # Primary key: category name (case-insensitive)
    # Secondary key: artist name (case-insensitive)
    sorted_data = sorted(link_data, key=lambda x: (x['category'].lower(), x['artist'].lower()))

    # 2. Group data by category
    categories_data = {}
    for item in sorted_data:
        category = item['category']
        if category not in categories_data:
            categories_data[category] = []
        categories_data[category].append(item)

    # 3. Generate the new HTML content
    soup = BeautifulSoup(HTML_TEMPLATE, "html.parser")
    body = soup.find("body")
    if not body:
        return False

    # Remove existing content after <h1> (Deezer Favourites)
    h1 = body.find("h1")
    if h1:
        for element in list(h1.next_siblings):
            element.extract()

    # 4. Write sorted categories and links to the soup object
    for category_name in sorted(categories_data.keys()):
        category_links = categories_data[category_name]

        # Category Div
        categorydiv = soup.new_tag("div", attrs={"class": "category"})
        header = soup.new_tag("h2")
        header.string = category_name
        categorydiv.append(header)

        # Links
        for item in category_links:
            linkdiv = soup.new_tag("div", attrs={"class": "link-item"})
            linktag = soup.new_tag("a", href=item['url'], target="_blank")
            # Link text is "Artist - Album"
            linktag.string = f"{item['artist']} - {item['album']}" 
            linkdiv.append(linktag)
            categorydiv.append(linkdiv)

        body.append(categorydiv)

    # 5. Write the prettified HTML back to the file
    with open(HTMLFILENAME, "w", encoding="utf-8") as f:
        f.write(str(soup.prettify()))

    return True

def centerwindow(root, width=500, height=250):
    screenwidth = root.winfo_screenwidth()
    screenheight = root.winfo_screenheight()
    x = int(screenwidth/2 - width/2)
    y = int(screenheight/2 - height/2)
    root.geometry(f"{width}x{height}+{x}+{y}")

def parsedeezeralbumurl(url):
    """Fetches and parses artist and album names from a Deezer album URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        titletag = soup.find("title")
        albumname = None
        artistname = None

        # Try Deezer-specific title
        if titletag:
            titletext = titletag.text
            if " - Album by " in titletext:
                albumname = titletext.split(" - Album by ")[0].strip()
                try:
                    # Get artist name before the "|" or end of string
                    artistname = titletext.split(" - Album by ")[1].split("|")[0].strip()
                except:
                    artistname = None
        if not albumname:
            h1 = soup.find("h1")
            if h1:
                albumname = h1.text.strip()
                
        # Robustly parse artist from the meta description, fixing the original parsing issue
        metadesc = soup.find("meta", attrs={"name": "description"})
        if metadesc:
            desc = metadesc.get("content", "")
            if " by " in desc:
                artistsection = desc.split(" by ", 1)[1].strip()

                # Clean up artist name from description by splitting on common markers
                if " on Deezer" in artistsection:
                    artistsection = artistsection.split(" on Deezer", 1)[0].strip()
                elif "." in artistsection: # Fallback for other periods
                    artistsection = artistsection.split(".", 1)[0].strip()

                if "from" in artistsection:
                    artistsection = artistsection.split("from")[0].strip()

                artistname = artistsection
                
        # More fallback options
        if not artistname:
            artistelement = soup.find("a", class_="link-artist")
            if artistelement:
                artistname = artistelement.text.strip()
        if not artistname:
            ariaartist = soup.find(attrs={"aria-label": True})
            if ariaartist:
                artistname = ariaartist["aria-label"].strip()

        if not albumname or not artistname:
            return None, None
        return artistname, albumname
    except Exception:
        return None, None

def creategui():
    # Load data to get current categories for the combobox
    _, categories = load_data_from_html()
    root = Tk()
    root.title("Deezer Favourites Manager")
    root.resizable(False, False)
    centerwindow(root, 500, 250)

    categoryvar = StringVar()
    urlvar = StringVar()
    newcategoryvar = StringVar()

    Label(root, text="Category:").pack(pady=5)
    combo = ttk.Combobox(root, textvariable=categoryvar)
    combovalues = categories + ["Add new category"]
    combo["values"] = combovalues
    combo.pack(fill="x", padx=20)

    Label(root, text="New Category Name:").pack(pady=5)
    newcatentry = Entry(root, textvariable=newcategoryvar, state="disabled")
    newcatentry.pack(fill="x", padx=20)

    Label(root, text="Deezer Album URL:").pack(pady=5)
    urlentry = Entry(root, textvariable=urlvar)
    urlentry.pack(fill="x", padx=20)

    def oncategorychange(event=None):
        if categoryvar.get() == "Add new category":
            newcatentry.config(state="normal")
        else:
            newcatentry.config(state="disabled")
            newcategoryvar.set("")
    combo.bind("<<ComboboxSelected>>", oncategorychange)

    def submit():
        selected = categoryvar.get().strip()
        url = urlvar.get().strip()
        newcatname = newcategoryvar.get().strip()
        
        # --- Validation ---
        if not selected:
            messagebox.showerror("Error", "Please enter or select a category.")
            return
        if selected == "Add new category" and not newcatname:
            messagebox.showerror("Error", "Please enter the new category name.")
            return
        if not url or not url.startswith("http"):
            messagebox.showerror("Error", "Please enter a valid Deezer album URL.")
            return
            
        artist, album = parsedeezeralbumurl(url)
        if not artist or not album:
            messagebox.showerror("Error", "Could not parse artist or album from Deezer link.")
            return
            
        # --- Core Logic Refactored ---
        # 1. Load existing data
        link_data, _ = load_data_from_html()

        # 2. Determine final category
        final_category = newcatname if selected == "Add new category" else selected

        # 3. Add the new link to the array
        new_link = {
            'category': final_category,
            'artist': artist,
            'album': album,
            'url': url
        }
        link_data.append(new_link)

        # 4. Write the entire sorted array back to HTML
        success = write_data_to_html(link_data)

        if success:
            result = messagebox.askyesno("Done", f"Link added:\n{artist} - {album}\nAdd another?")
            root.destroy()
            if result:
                # Re-run the GUI
                root.quit()
            else:
                sys.exit(0)
        else:
             messagebox.showerror("Error", "Failed to write data to HTML file.")


    def closeprogram():
        root.destroy()
        sys.exit(0)

    buttonframe = Frame(root)
    buttonframe.pack(pady=15)
    addbutton = Button(buttonframe, text="Add Link", command=submit, bg="#0078D7", fg="white")
    addbutton.pack(side=LEFT, padx=5)
    closebutton = Button(buttonframe, text="Close", command=closeprogram)
    closebutton.pack(side=LEFT, padx=5)

    root.mainloop()

def gui():
    ensurehtmlfile()
    while True:
        creategui()

if __name__ == "__main__":
    gui()
