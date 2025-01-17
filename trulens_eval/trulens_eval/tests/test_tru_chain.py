# from llama.hf import LLaMATokenizer

import pinecone
import pytest
import torch
from transformers import AutoModelForCausalLM
from transformers import AutoTokenizer
from transformers import pipeline

from trulens_eval.keys import PINECONE_API_KEY
from trulens_eval.keys import PINECONE_ENV
from trulens_eval.tru_chain import TruChain
from trulens_eval.util import OptionalImports
from trulens_eval.util import REQUIREMENT_LANGCHAIN

with OptionalImports(message=REQUIREMENT_LANGCHAIN):
    from langchain import LLMChain
    from langchain import PromptTemplate
    from langchain.chains import ConversationalRetrievalChain
    from langchain.chains import SimpleSequentialChain
    from langchain.embeddings.openai import OpenAIEmbeddings
    from langchain.llms import HuggingFacePipeline
    from langchain.memory import ConversationBufferWindowMemory
    from langchain.vectorstores import Pinecone


class TestTruChain():

    def setup_method(self):
        print("setup")

        self.llm_model_id = "gpt2"
        # This model is pretty bad but using it for tests because it is free and
        # relatively small.

        # model_id = "decapoda-research/llama-7b-hf"
        # model_id = "decapoda-research/llama-13b-hf"

        self.model = AutoModelForCausalLM.from_pretrained(
            self.llm_model_id,
            device_map='auto',
            torch_dtype=torch.float16,
            local_files_only=True
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.llm_model_id, local_files_only=True
        )

        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=16,
            device_map="auto",
            early_stopping=True
        )

        self.llm = HuggingFacePipeline(pipeline=self.pipe)

    def test_qa_prompt(self):
        # Test of a small q/a app using a prompt and a single call to an llm.

        # llm = OpenAI()

        template = """Q: {question} A:"""
        prompt = PromptTemplate(template=template, input_variables=["question"])
        llm_app = LLMChain(prompt=prompt, llm=self.llm)

        tru_app = TruChain(app=llm_app)

        assert tru_app.app is not None

        tru_app.run(dict(question="How are you?"))
        tru_app.run(dict(question="How are you today?"))

        assert len(tru_app.db.select()) == 2

    def test_qa_prompt_with_memory(self):
        # Test of a small q/a app using a prompt and a single call to an llm.
        # Also has memory.

        # llm = OpenAI()

        template = """Q: {question} A:"""
        prompt = PromptTemplate(template=template, input_variables=["question"])

        memory = ConversationBufferWindowMemory(k=2)

        llm_app = LLMChain(prompt=prompt, llm=self.llm, memory=memory)

        tru_app = TruChain(app=llm_app)

        assert tru_app.app is not None

        tru_app.run(dict(question="How are you?"))
        tru_app.run(dict(question="How are you today?"))

        assert len(tru_app.db.select()) == 2

    @pytest.mark.nonfree
    def test_qa_db(self):
        # Test a q/a app that uses a vector store to look up context to include in
        # llm prompt.

        # WARNING: this test incurs calls to pinecone and openai APIs and may cost money.

        index_name = "llmdemo"

        embedding = OpenAIEmbeddings(
            model='text-embedding-ada-002'
        )  # 1536 dims

        pinecone.init(
            api_key=PINECONE_API_KEY,  # find at app.pinecone.io
            environment=PINECONE_ENV  # next to api key in console
        )
        docsearch = Pinecone.from_existing_index(
            index_name=index_name, embedding=embedding
        )

        # llm = OpenAI(temperature=0,max_tokens=128)

        retriever = docsearch.as_retriever()
        app = ConversationalRetrievalChain.from_llm(
            llm=self.llm, retriever=retriever, return_source_documents=True
        )

        tru_app = TruChain(app)
        assert tru_app.app is not None
        tru_app(dict(question="How do I add a model?", chat_history=[]))

        assert len(tru_app.db.select()) == 1

    def test_sequential(self):
        # Test of a sequential app that contains the same llm twice with
        # different prompts.

        template = """Q: {question} A:"""
        prompt = PromptTemplate(template=template, input_variables=["question"])
        llm_app = LLMChain(prompt=prompt, llm=self.llm)

        template_2 = """Reverse this sentence: {sentence}."""
        prompt_2 = PromptTemplate(
            template=template_2, input_variables=["sentence"]
        )
        llm_app_2 = LLMChain(prompt=prompt_2, llm=self.llm)

        seq_app = SimpleSequentialChain(
            apps=[llm_app, llm_app_2],
            input_key="question",
            output_key="answer"
        )
        seq_app.run(
            question="What is the average air speed velocity of a laden swallow?"
        )

        tru_app = TruChain(seq_app)
        assert tru_app.app is not None

        # This run should not be recorded.
        seq_app.run(
            question="What is the average air speed velocity of a laden swallow?"
        )

        # These two should.
        tru_app.run(
            question=
            "What is the average air speed velocity of a laden european swallow?"
        )
        tru_app.run(
            question=
            "What is the average air speed velocity of a laden african swallow?"
        )

        assert len(tru_app.db.select()) == 2
