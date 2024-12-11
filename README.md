## Louisiana French Language Preservation
This project explores the use of AI language models to help preserve the unique French dialect of South Louisiana.

### Overview
- Compiled a parallel corpus of Louisiana French and English text
- Evaluated the feasibility of training a translation model on the corpus
- Designed a system architecture to integrate the language model into a preservation platform
- Developed a prototype interface for testing the initial translation capabilities

### Prototype
A simple prototype interface built with Gradio is made available at the following link to serve as a proof of concept:
<div align="center">
  [Louisiana French Translator Prototype](https://huggingface.co/spaces/c-walls/Louisiana-French)
</div>
This prototype showcases the basic translation functionality that could be further developed. Translations are produced by the custom NLLB-200 model trained on the corpus compiled for this project. The learning path interface serves only as a mock-up of potential functionality. Lastly, the chatbot is currently powered by Zepher-7B, which is much smaller than the frontier models typically used for this kind of task, as a result, it is not nearly as effective as those larger models for facilitating learning-centric interactions.
