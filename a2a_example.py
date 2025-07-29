# -*- coding: utf-8 -*-
"""
Agent A2A d’exemple : renvoie les messages utilisateur en MAJUSCULES.

Correction :
  • compatibilité SDK a2a >= 0.5 : context.params ⇒ context._params
    (fallback automatique si .params revient plus tard).
  • oubli de « await » sur event_queue.enqueue_event() corrigé.
"""

import asyncio
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Message,
    MessageSendParams,
)
from a2a.utils import new_agent_text_message
from a2a.server.apps import A2AStarletteApplication


# --------------------------------------------------------------------------- #
# Logique métier : transformer un texte en majuscules                         #
# --------------------------------------------------------------------------- #
class UppercaseAgent:
    """Agent minimal : transforme le texte en majuscules."""

    async def transform(self, text: str) -> str:
        # petite latence simulée
        await asyncio.sleep(0.1)
        return text.upper()


# --------------------------------------------------------------------------- #
# Exécuteur qui relie l’agent aux requêtes A2A                                #
# --------------------------------------------------------------------------- #
class UppercaseAgentExecutor(AgentExecutor):
    """Implémentation de AgentExecutor pour l’écho en MAJUSCULES."""

    def __init__(self) -> None:
        self.agent = UppercaseAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Gère les appels message/send et message/stream.

        Étapes :
          1. Récupérer le Message utilisateur (params.message)
          2. Extraire le texte
          3. Le transformer
          4. Enfiler la réponse dans la file d’événements
        """
        # 1. Récupérer les paramètres du message (SDK a2a >= 0.5 : ._params)
        params: MessageSendParams = getattr(context, "params", context._params)
        user_message: Message = params.message

        # 2. Concaténer les morceaux de texte
        user_text = " ".join(
            part.text for part in user_message.parts if getattr(part, "text", None)
        )

        # 3. Transformer
        transformed = await self.agent.transform(user_text)

        # 4. Enfiler la réponse (IMPORTANT : await)
        response_message = new_agent_text_message(transformed)
        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Annulation non prise en charge pour cet agent."""
        raise Exception("cancel not supported")


# --------------------------------------------------------------------------- #
# Définition du skill et de la carte agent                                    #
# --------------------------------------------------------------------------- #
skill = AgentSkill(
    id="uppercase",
    name="Uppercase Echo",
    description="Retourne le texte en majuscules.",
    tags=["echo", "uppercase"],
    examples=["bonjour", "hello"],
    input_modes=["text"],
    output_modes=["text"],
)

agent_card = AgentCard(
    name="Uppercase Agent",
    description="Un agent qui met vos messages en majuscules.",
    url="http://localhost:9999/",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
    supports_authenticated_extended_card=False,
)

# --------------------------------------------------------------------------- #
# Construction et démarrage de l’application Starlette                        #
# --------------------------------------------------------------------------- #
request_handler = DefaultRequestHandler(
    agent_executor=UppercaseAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

# Application ASGI exposée pour Uvicorn
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()

# Lance le serveur avec :
#   uvicorn a2a_example:app --host 0.0.0.0 --port 9999 --reload
