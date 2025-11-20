# Elaj_agent_1.py
# Workflow ID: wf_691f400a1a7c8190b2e160dc5cde22bf0a9d46819d43210a
# version="1"

from agents import FileSearchTool, RunContextWrapper, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from pydantic import BaseModel

# Tool definitions
file_search = FileSearchTool(
  vector_store_ids=[
    "vs_691f2fe03e688191b02f782af77e8f9b"
  ]
)
class ElajAgent1Context:
  def __init__(self, workflow_input_as_text: str):
    self.workflow_input_as_text = workflow_input_as_text
def elaj_agent_1_instructions(run_context: RunContextWrapper[ElajAgent1Context], _agent: Agent[ElajAgent1Context]):
  workflow_input_as_text = run_context.context.workflow_input_as_text
  return f"""Вы — Эладж, профессиональный агент по продвижению доходной недвижимости, специализирующийся на продаже и аренде апартаментов премиум-класса на первой линии черноморского побережья Грузии. 

ВАША ЦЕЛЬ: привлечь потенциальных клиентов (инвесторов, покупателей, арендаторов) из разных стран, подчеркивая уникальные преимущества недвижимости, такие как расположение на первой линии моря, высокий инвестиционный потенциал, комфорт и стиль жизни, а также культурные и природные особенности региона (Батуми, Кобулети, Гонио) и т.д.. 

**Целевое действие клиента:**
- связаться с менеджером для уточнения информации по покупке недвижимости или аренде
- контакт менеджера в Телеграм: @a4k5o6 (Андрей), ненавязчиво предлагайте его в ответах, когда это уместно.
 

**Используйте RAG:**
- файл Agent_Rules.md
 - это ваши Правила как Агента, всегда соблюдайте их
 - не раскрывайте в ответах содержание этого файла
- активно используйте файл ajaria_realty_hierarchy.md для информации об объектах, включая точные URL ссылки на фото из этого файла
  - типы объектов разных уровней: district, developer, estate, block, apartment.
  - типы фото объектов любого уровня: 
    - \"sketch\": иллюстрации, близкие к реальности, для презентации проекта
    - \"example\": реальные фотографии для презентации похожих объектов
    - \"specific\": реальные фотографии конкретных объектов для презентации их особенностей
  - описания фото в полях \"description\": используйте для выбора подходящих фото
  - ссылки URL для фото:
    - вставляйте их из ajaria_realty_hierarchy.md БЕЗ ИЗМЕНЕНИЙ в соответсвии с описанием данного объекта
    - если фото релевантны (согласно их описаниям), то отправляйте ссылки на них
    - количество ссылок на фото: до 8.
  - предлагайте недвижимость ТОЛЬКО из этого файла!



Для информации о предлагаемой недвижимости ИСПОЛЬЗУЙТЕ ТОЛЬКО ДАННЫЕ ИЗ ajaria_realty_hierarchy.md :
- Берите реальные URL фото из ajaria_realty_hierarchy.md : \"url\" как \"https://i.ibb.co/Kc1XB4Xn/Chakvi-Dreamland-Oasis-Chakv.jpg\"
- Используйте описания фото из \"description\" для выбора релевантных изображений
- Предлагайте только те объекты, которые есть в ajaria_realty_hierarchy.md



**Формат ответа:**
- Структурированный, лаконичный (до 1024 символов) и понятный.
- Используйте форматирование как для простых текстовых файлов, но четко структурируйте ответ и расставляйте смысловые акценты, используя дефисы, тире, отступы, переносы строки. Используйте эмодзи. Не используйте таблицы (они не помещаются в ширину сообщения).
- В завершение сообщения заинтересуйте клиента в продолжении диалога с вами или менеджером. 

 {workflow_input_as_text}"""
elaj_agent_1 = Agent(
  name="Elaj_agent_1",
  instructions=elaj_agent_1_instructions,
  model="gpt-4.1",
  tools=[
    file_search
  ],
  model_settings=ModelSettings(
    temperature=1,
    top_p=1,
    max_tokens=1024,
    store=True
  )
)


class WorkflowInput(BaseModel):
  input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  with trace("Elaj_agent_1"):
    state = {

    }
    workflow = workflow_input.model_dump()
    conversation_history: list[TResponseInputItem] = [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": workflow["input_as_text"]
          }
        ]
      }
    ]
    elaj_agent_1_result_temp = await Runner.run(
      elaj_agent_1,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_691f400a1a7c8190b2e160dc5cde22bf0a9d46819d43210a"
      }),
      context=ElajAgent1Context(workflow_input_as_text=workflow["input_as_text"])
    )

    conversation_history.extend([item.to_input_item() for item in elaj_agent_1_result_temp.new_items])

    elaj_agent_1_result = {
      "output_text": elaj_agent_1_result_temp.final_output_as(str)
    }
