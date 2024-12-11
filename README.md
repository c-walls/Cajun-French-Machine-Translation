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

This prototype showcases the basic translation functionality that could be further developed. Translations are produced by the custom NLLB-200 model trained on the corpus compiled for this project. The learning path interface serves only as a mock-up of potential functionality. Lastly, the chatbot is currently powered by Zepher-7B, which is much smaller than the frontier models typically used for this kind of task, as a result, it is not nearly as effective as those larger models for facilitating learning-centric interactions.
