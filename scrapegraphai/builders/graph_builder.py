"""
GraphBuilder Module
"""

from langchain.chains import create_extraction_chain
from langchain_community.chat_models import ErnieBotChat
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..helpers import graph_schema, nodes_metadata


class GraphBuilder:
    """
    GraphBuilder is a dynamic tool for constructing web scraping graphs based on user prompts.
    It utilizes a natural language understanding model to interpret user prompts and
    automatically generates a graph configuration for scraping web content.

    Attributes:
        prompt (str): The user's natural language prompt for the scraping task.
        llm (ChatOpenAI): An instance of the ChatOpenAI class configured
        with the specified llm_config.
        nodes_description (str): A string description of all available nodes and their arguments.
        chain (LLMChain): The extraction chain responsible for
        processing the prompt and creating the graph.

    Methods:
        build_graph(): Executes the graph creation process based on the user prompt
        and returns the graph configuration.
        convert_json_to_graphviz(json_data): Converts a JSON graph configuration
        to a Graphviz object for visualization.

    Args:
        prompt (str): The user's natural language prompt describing the desired scraping operation.
        url (str): The target URL from which data is to be scraped.
        llm_config (dict): Configuration parameters for the
            language model, where 'api_key' is mandatory,
            and 'model_name', 'temperature', and 'streaming' can be optionally included.

    Raises:
        ValueError: If 'api_key' is not included in llm_config.
    """

    def __init__(self, prompt: str, config: dict):
        """
        Initializes the GraphBuilder with a user prompt and language model configuration.
        """
        self.prompt = prompt
        self.config = config
        self.llm = self._create_llm(config["llm"])
        self.nodes_description = self._generate_nodes_description()
        self.chain = self._create_extraction_chain()

    def _create_llm(self, llm_config: dict):
        """
        Creates an instance of the OpenAI class with the provided language model configuration.

        Returns:
            OpenAI: An instance of the OpenAI class.

        Raises:
            ValueError: If 'api_key' is not provided in llm_config.
        """
        llm_defaults = {"temperature": 0, "streaming": True}
        llm_params = {**llm_defaults, **llm_config}
        if "api_key" not in llm_params:
            raise ValueError("LLM configuration must include an 'api_key'.")

        if "gpt-" in llm_params["model"]:
            return ChatOpenAI(llm_params)
        elif "gemini" in llm_params["model"]:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise ImportError(
                    "langchain_google_genai is not installed. Please install it using 'pip install langchain-google-genai'."
                )
            return ChatGoogleGenerativeAI(llm_params)
        elif "ernie" in llm_params["model"]:
            return ErnieBotChat(llm_params)
        raise ValueError("Model not supported")

    def _generate_nodes_description(self):
        """
        Generates a string description of all available nodes and their arguments.

        Returns:
            str: A string description of all available nodes and their arguments.
        """

        return "\n".join(
            [
                f"""- {node}: {data["description"]} (Type: {data["type"]},
            Args: {", ".join(data["args"].keys())})"""
                for node, data in nodes_metadata.items()
            ]
        )

    def _create_extraction_chain(self):
        """
        Creates an extraction chain for processing the user prompt and
        generating the graph configuration.

        Returns:
            LLMChain: An instance of the LLMChain class.
        """

        create_graph_prompt_template = """
        You are an AI that designs direct graphs for web scraping tasks.
        Your goal is to create a web scraping pipeline that is efficient and tailored to the user's requirements.
        You have access to a set of default nodes, each with specific capabilities:

        {nodes_description}

        Based on the user's input: "{input}", identify the essential nodes required for the task and suggest a graph configuration that outlines the flow between the chosen nodes.
        """.format(nodes_description=self.nodes_description, input="{input}")
        extraction_prompt = ChatPromptTemplate.from_template(
            create_graph_prompt_template
        )
        return create_extraction_chain(
            prompt=extraction_prompt, schema=graph_schema, llm=self.llm
        )

    def build_graph(self):
        """
        Executes the graph creation process based on the user prompt and
         returns the graph configuration.

        Returns:
            dict: A JSON representation of the graph configuration.
        """
        return self.chain.invoke(self.prompt)

    @staticmethod
    def convert_json_to_graphviz(json_data, format: str = "pdf"):
        """
        Converts a JSON graph configuration to a Graphviz object for visualization.

        Args:
            json_data (dict): A JSON representation of the graph configuration.

        Returns:
            graphviz.Digraph: A Graphviz object representing the graph configuration.
        """
        try:
            import graphviz
        except ImportError:
            raise ImportError(
                "The 'graphviz' library is required for this functionality. "
                "Please install it from 'https://graphviz.org/download/'."
            )

        graph = graphviz.Digraph(
            comment="ScrapeGraphAI Generated Graph",
            format=format,
            node_attr={"color": "lightblue2", "style": "filled"},
        )

        graph_config = json_data["text"][0]

        # Retrieve nodes, edges, and the entry point from the JSON data
        nodes = graph_config.get("nodes", [])
        edges = graph_config.get("edges", [])
        entry_point = graph_config.get("entry_point")

        for node in nodes:
            if node["node_name"] == entry_point:
                graph.node(node["node_name"], shape="doublecircle")
            else:
                graph.node(node["node_name"])

        for edge in edges:
            if isinstance(edge["to"], list):
                for to_node in edge["to"]:
                    graph.edge(edge["from"], to_node)
            else:
                graph.edge(edge["from"], edge["to"])

        return graph
