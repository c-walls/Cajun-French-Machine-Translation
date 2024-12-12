## Louisiana French Language Preservation
This project explored the use of AI language models to help preserve Louisiana French.

### Overview
- Compiled a parallel corpus of roughly 18K Louisiana French and English sentences
- Evaluated the feasibility of training a translation model on the corpus
- Designed a system architecture to integrate the language model into a public-facing application
- Developed a prototype to serve as a proof-of-concept and to use for testing the initial translation model's capabilities

### Prototype
A simple prototype interface built with Gradio is made available at the following link to serve as a proof of concept:

[Louisiana French Translator Prototype](https://huggingface.co/spaces/c-walls/Louisiana-French) 

This prototype showcases the basic translation functionality of the custom NLLB-200 model that was fine-tuned tuned on the parallel corpus compiled for this research project. The learning path interface serves only as a mock-up of potential functionality. Lastly, the chatbot is currently powered by Zepher-7B, which is much smaller than the frontier models typically used for this kind of task. As a result, it is much less effective than larger models at orchestrating conversational learning interactions. Regardless, as part of this prototyp, it demonstrates how these sorts of tools can be combined to make an effective learning interface. 

If you have trouble accessing or using the interface above, then use this [GOOGLE COLAB NOTEBOOK](https://colab.research.google.com/drive/1raMg-TpSXWfhNMLUl8XIkanC7wcEFQW6?usp=sharing) as an even simpler way to run inference on the model and test it's translation abilities.
