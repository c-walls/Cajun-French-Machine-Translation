import re
import tkinter as tk
from tkinter import ttk

dummy_eng_text = [
    ['She turned to me and said, “What’s wrong with you, Jim Soileau?',
    'You must have a drawer of milk curds in your brain.”',
    'She added, “You must be losing the little bit of a mind you have.”',
    'She was acting like she didn’t like my caresses.',
    'But man, I know how to get along with my wife, yeah.',
    'It’s much better to make believe she’s right than to let her begin to argue.'],
    ['Because, by thunder, when my wife starts quarreling, it’s like popcorn popping.',
    'I hear ta-ta-ta-ta-ta-ta-ta-ta-ta.',
    'It doesn’t end.',
    'Once supper was cooked and I sat down at the table, I told my wife, Clothilde, I said, “Listen, dear, put the cats out because I don’t want them brushing against my legs while I’m eating my possum.”',
    'By thunder!',
    'Man, that was a night!',
    'I ate so much that you could’ve played the drum on my stomach after I was finished.',
    'I guarantee you, man, that if I’d died that night, it wouldn’t have been from hunger.',
    'That’s why I want to say, my friends, that there’s no one in the world who could’ve had more trouble than me during the flood of ‘27.']
]

dummy_cajun_text = [
    ['À se retourne sus moi, a dit, «Ça i n-a avec toi, Jim Soileau?',
    'Tu dois avoir un tiroir de lait caillé dans ta cervelle.»',
    'A dit, «Tu dois être après perdre ton ti brin d’esprit que t’as.»',
    'À faisait comme alle aimait pas mes caresses.',
    'Mais, nègre, moi je connais appâter ma femme, ouais.',
    'C’est beaucoup mieux d’y faire à croire que la quitter commencer à disputer.'],
    ['Parce que, tonnerre mes chiens, quand ma femme commence à quereller, c’est comme un tac-tac qu’après fleurir.',
    'J’attends ta-ta-ta-ta-ta-ta-ta-ta-ta.',
    'N-a pus de finition.',
    'Quand le souper était cuit et je m’ai attablé, j’ai dit à ma femme, Clothilde, je dis «Écoute, chère, fous les chats dehors, parce que je veux pas que ça repasse dans mes jambes pendant j’sus après manger mon rat de bois.»',
    'Tonnerre mes chiens, nègre, ça c’est un soir.',
    'Jai tellement mangé jusqu’à t’aurais pu jouer le tambour sus mon estomac après que j’ai eu fini.',
    'Je t’en garantis, nègre, si je serais mort ce soir-là, ç’aurait pas été avec la faim.',
    'C’est pour ça je veux vous dire, mes amis, i n-a pas personne dans le monde entier qu’a doit eu plus de la misère que moi durant l’eau haute de °27.']
]

def load_text(text_widget, text):
    text_widget.delete("1.0", tk.END)
    for i, page in enumerate(text):
        text_widget.insert(tk.END, "\n________________________________ page " + str(i+1) + " ____________________________________\n\n\n")
        for line in page:
            text_widget.insert(tk.END, line + "\n\n")

def save_text(text_widget):
    text = text_widget.get("1.0", tk.END)
    text = re.sub(r'\n_{2,}.*_{2,}\n\n\n', '', text, count=1)
    pages = re.split(r'\n_{2,}.*_{2,}\n\n\n', text)
    pages = [page.split('\n\n') for page in pages]
    
    return pages

def create_editor():
    root = tk.Tk()
    root.title("Corpus Alignment Tool")
    root.geometry("1400x800")
    root.state("zoomed")

    # Create outer frame that dynamically resizes
    frame = ttk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(0, weight=1)

    # Create side-by-side text widgets
    text1 = tk.Text(frame, wrap="word")
    text1.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))
    text2 = tk.Text(frame, wrap="word")
    text2.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))

    # Load text into text widgets
    load_text(text1, dummy_eng_text)
    load_text(text2, dummy_cajun_text)

    # Create scrollbars
    scrollbar1 = ttk.Scrollbar(frame, orient="vertical", command=text1.yview)
    scrollbar1.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E))
    text1["yscrollcommand"] = scrollbar1.set
    scrollbar2 = ttk.Scrollbar(frame, orient="vertical", command=text2.yview)
    scrollbar2.grid(column=1, row=0, sticky=(tk.N, tk.S, tk.E))
    text2["yscrollcommand"] = scrollbar2.set

    root.mainloop()

if __name__ == "__main__":
    create_editor()