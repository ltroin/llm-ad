from universalmodels import ModelInfo, pretrained_from_info, model_info_from_name, ModelSrc

from src.framework.framework_model import FrameworkModel
from src.strings import PROMPT_CRITIQUE_PROMPT, RESPONSE_CRITIQUE_PROMPT, CONSCIENCE_DISCLAIMER_PROMPT, RESPONSE_CORRECTION_PROMPT


class Secondary(FrameworkModel):
    """The conscience model.  This examines both the user input and model output for alignment violations"""

    def __init__(self, critique_model_info: ModelInfo, rephrase_model_info: ModelInfo):
        """
        Args:
            critique_model_info: The information for the critique model
            rephrase_model_info: The information for the rephrasing model"""

        self.critique_model, self.critique_tokenizer = pretrained_from_info(critique_model_info)
        self.rephrase_model, self.rephrase_tokenizer = pretrained_from_info(rephrase_model_info)

    @classmethod
    def from_model_names(cls, secondary_model_name: str, rephrase_model_name: str = "dev/echo",
                         secondary_model_src: ModelSrc = ModelSrc.AUTO, rephrase_model_src: ModelSrc = ModelSrc.AUTO):
        """Creates a secondary model from the names of its primary and secondary models

        Args:
            secondary_model_name: The name of the secondary model
            rephrase_model_name: The name of the rephrasing model
            secondary_model_src: The suggested source of the secondary model to load. Defaults to AUTO
            rephrase_model_src: The suggested source of the rephrasing model to load. Defaults to AUTO
        Returns:
            An instance of a secondary model"""

        s_model_info = model_info_from_name(secondary_model_name, model_src=secondary_model_src, model_task="conversational")
        # Optional rephrasing model
        rephrase_model_info = model_info_from_name(rephrase_model_name, model_src=rephrase_model_src, model_task="summarization")

        return cls(s_model_info, rephrase_model_info)

    @property
    def name(self):
        return f"S({self.critique_model.name_or_path})"

    def generate(self, prompt: str, **kwargs):
        """Generates a response to the prompt from the critique model

        Args:
            prompt: The prompt to generate a response for
        Returns:
            The generated response string"""

        return self.generate_using(prompt, self.critique_model, self.critique_tokenizer, **kwargs)

    def rephrase(self, text: str, **kwargs):
        """Rephrase the given text by using the rephrasing model

        Args:
            text: The text to rephrase
        Returns:
            The rephrased text"""

        return self.generate_using(text, self.rephrase_model, self.rephrase_tokenizer, **kwargs)

    def critique_prompt(self, prompt: str, **kwargs):
        """Generates a critique of the given prompt.  If harmful or dangerous contents are detected, a suggestion will be generated

        Args:
            prompt: The prompt to generate a critique for
        Returns:
            The generated critique for the prompt"""

        critique_response = self.generate_using(PROMPT_CRITIQUE_PROMPT.format(prompt=prompt), self.critique_model, self.critique_tokenizer, **kwargs)
        return critique_response if self.is_valid_critique(critique_response) else ""

    def critique_response(self, response: str, **kwargs):
        """Generates a critique of the given response.  If harmful or dangerous contents are detected, a suggestion will be generated

        Args:
            response: The response to generate a critique for
        Returns:
            The generated critique for the response"""

        critique_response = self.generate_using(RESPONSE_CRITIQUE_PROMPT.format(response=response), self.critique_model, self.critique_tokenizer, **kwargs)
        return critique_response if self.is_valid_critique(critique_response) else ""

    @staticmethod
    def make_conscience_prompt(prompt: str, prompt_critique: str):
        """Formats a prompt, so it contains the prompt itself and a critique from the model's "conscience"

        Args:
            prompt: The prompt originally given to the primary model
            prompt_critique: The generated critique for the prompt
        Returns:
            The formatted conscience prompt to be given back to the primary model"""

        return CONSCIENCE_DISCLAIMER_PROMPT.format(prompt_critique=prompt_critique, prompt=prompt)

    @staticmethod
    def make_correction_prompt(response: str, response_critique: str):
        """Formats a response, so it contains the response itself and a critique for correction by the primary model

        Args:
            response: The response originally generated by the primary model
            response_critique: The generated critique for the response
        Returns:
            The formatted correction prompt to be given back to the primary model"""

        return RESPONSE_CORRECTION_PROMPT.format(response=response, response_critique=response_critique)

    @staticmethod
    def is_valid_critique(critique: str):
        """Checks if a critique positively identifies some text as unsafe.  Returns false if no unsafe critique markers are present, true otherwise

        Args:
            critique: The critique generated for some text
        Returns:
            Whether the given critique positively identifies text as unsafe"""

        no_critique_flags = ["no change", "not change", "not adversarial"]
        for flag in no_critique_flags:
            if flag.lower() in critique.lower():
                return False
        return True
