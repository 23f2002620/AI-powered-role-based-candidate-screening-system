# AI/ML Engineering Knowledge Base

## Machine Learning Foundations
Supervised learning maps inputs to labeled outputs (classification, regression); unsupervised
learning finds structure without labels (clustering, dimensionality reduction); reinforcement
learning learns a policy through reward signals from an environment. The bias-variance tradeoff
describes underfitting (high bias) versus overfitting (high variance); regularization (L1/Lasso
for sparsity, L2/Ridge for shrinkage, dropout for neural nets) mitigates overfitting. Cross-
validation (k-fold, stratified k-fold) estimates generalization performance. Evaluation metrics
include accuracy, precision, recall, F1, ROC-AUC for classification and MAE, RMSE, R^2 for
regression; the right metric depends on class imbalance and the cost of false positives versus
false negatives.

## Deep Learning
Neural networks learn hierarchical feature representations through layers of weighted
transformations and nonlinear activations (ReLU, GELU, sigmoid, tanh). Backpropagation computes
gradients via the chain rule; optimizers (SGD with momentum, Adam, AdamW) update weights using
those gradients, with learning rate schedules (cosine decay, warmup) affecting convergence.
Batch normalization and layer normalization stabilize training by controlling internal covariate
shift. Convolutional Neural Networks (CNNs) exploit spatial locality and weight sharing for
vision tasks; Recurrent Neural Networks (RNNs, LSTMs, GRUs) model sequences but suffer from
vanishing gradients over long sequences, which motivated attention mechanisms.

## Transformers and Large Language Models
The Transformer architecture replaces recurrence with self-attention, allowing parallel
computation over sequence positions. Scaled dot-product attention computes queries, keys, and
values; multi-head attention lets the model attend to different representation subspaces
simultaneously. Positional encodings (sinusoidal or learned, or rotary embeddings like RoPE)
inject order information since attention itself is permutation-invariant. Pretraining objectives
include causal language modeling (predict next token, used by GPT-style decoder-only models) and
masked language modeling (predict masked tokens, used by BERT-style encoders). Fine-tuning
adapts a pretrained model to a downstream task; instruction tuning and RLHF (Reinforcement
Learning from Human Feedback) align model outputs with human preferences. Parameter-efficient
fine-tuning methods like LoRA (Low-Rank Adaptation) freeze base weights and learn small low-rank
update matrices, reducing compute and storage cost.

## Retrieval-Augmented Generation (RAG)
RAG systems ground generation in retrieved documents to reduce hallucination and provide
up-to-date or proprietary knowledge without retraining the model. A typical pipeline: chunk
source documents (fixed-size, semantic, or recursive character splitting, often with overlap to
preserve context across boundaries), embed chunks with a dense encoder, store vectors in a
vector database (FAISS, Pinecone, Chroma, Weaviate) that supports approximate nearest neighbor
search (HNSW, IVF), then at query time embed the user query and retrieve the top-k most similar
chunks to include as context in the prompt. Retrieval quality depends on chunk size (too large
dilutes relevance, too small loses context), embedding model choice, and whether hybrid search
(combining sparse keyword search like BM25 with dense vector search) is used, which often
outperforms either alone. Re-ranking retrieved chunks with a cross-encoder before final context
selection can further improve precision.

## Embeddings and Vector Search
Embeddings map discrete tokens or documents into continuous vector spaces where semantic
similarity corresponds to geometric proximity, typically measured with cosine similarity or dot
product. Approximate nearest neighbor algorithms trade a small amount of recall for large gains
in query speed: HNSW builds a navigable small-world graph; IVF partitions the space into Voronoi
cells and searches only the nearest few. Dimensionality reduction (PCA, t-SNE, UMAP) helps
visualize or compress embeddings but t-SNE/UMAP distances are not globally meaningful, only
locally so.

## MLOps and Productionization
Model serving considerations include latency, throughput, and batching (dynamic batching can
trade a small latency increase for large throughput gains). Model versioning and experiment
tracking (MLflow, Weights & Biases) support reproducibility. Data and concept drift monitoring
detects when a production model's assumptions no longer hold, since real-world distributions
change over time (e.g. user behavior shifts). A/B testing and shadow deployments validate model
changes before full rollout. Feature stores centralize feature computation to avoid
training-serving skew, where features computed offline for training differ subtly from those
computed online at inference time.

## Practical Considerations and Failure Modes
Hallucination in generative models refers to confident but unsupported or fabricated output;
grounding via retrieval, citations, and calibrated uncertainty estimates reduces but does not
eliminate this. Prompt injection is a security concern where untrusted input in context can
override intended instructions. Evaluation of generative systems is harder than classic ML
metrics allow; techniques include human evaluation, LLM-as-judge scoring, and task-specific
benchmarks, each with known biases (e.g. LLM judges can favor longer or more confident-sounding
answers).
