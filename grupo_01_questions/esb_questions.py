"""Grupo 1 - Editor de preguntas y atributos del ES-Shell Suite.

Modulo de adquisicion de conocimiento (categoria 2 del shell). Permite que el
experto del dominio cree, edite, valide y guarde los atributos y preguntas de
`conocimiento_dominio.json` sin modificar el codigo del motor de inferencia.

Este archivo expone:

- ``Attribute``: estructura de un atributo (lo que el shell le pregunta al
  usuario y los valores que acepta).
- ``DependsOn``: condicion que vuelve una pregunta condicional.
- ``QuestionEditor``: clase principal del modulo. Agrega, edita, borra, lista,
  valida y persiste atributos.
- Excepciones: ``AttributeExistsError``, ``AttributeNotFoundError``,
  ``ValidationError``.

Alcance del stub (Semana 11):

Los metodos de almacenamiento en memoria (``add``, ``edit``, ``delete``,
``get``, ``list``) ya funcionan. ``validate``, ``save_to_json`` y
``load_from_json`` estan declarados con sus firmas y levantan
``NotImplementedError``; se implementan en el Sprint 1 (ver README.md).

Contrato de datos: la propuesta del Grupo 4 (SchemaManager) es la base. Los
nombres de campo (``id``, ``name``, ``type``, ``question``, ``range``,
``options``) se mantienen fijos; ``help_text`` y ``depends_on`` son
ampliaciones propuestas por el Grupo 1 para preguntas condicionales y texto
de ayuda.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# Tipos aceptados por el contrato propuesto por el Grupo 4.
TIPOS_VALIDOS = ("numeric", "categorical", "boolean", "text")

# Operadores que puede usar una pregunta condicional. Se mantienen alineados
# con los operadores de regla propuestos por el Grupo 4.
OPERADORES_VALIDOS = ("==", "!=", ">", "<", ">=", "<=")


class AttributeExistsError(ValueError):
    """Se intenta agregar un atributo cuyo id ya esta en el editor."""


class AttributeNotFoundError(LookupError):
    """Se busca, edita o borra un atributo que no existe en el editor."""


class ValidationError(ValueError):
    """La base de atributos no cumple las reglas de validacion."""


@dataclass
class DependsOn:
    """Condicion que hace que una pregunta sea condicional.

    Significa: 'esta pregunta solo se le hace al usuario si, en el momento de
    preguntarla, el valor de ``attribute_id`` cumple ``operator value``'.

    Ejemplo: una pregunta 'Nombre del trabajo de graduacion' que solo aparece
    si antes se respondio ``materia == 'Trabajo de Graduacion'``.
    """

    attribute_id: str
    operator: str
    value: Any


@dataclass
class Attribute:
    """Un atributo del conocimiento del dominio.

    Campos obligatorios: ``id``, ``name``, ``type``.

    Campos opcionales:
    - ``question``: texto que ve el usuario. Puede faltar en atributos que
      solo se usan como conclusion y no se preguntan.
    - ``range``: ``[minimo, maximo]`` para atributos numericos.
    - ``options``: lista de opciones para atributos categoricos. Admite
      strings simples o diccionarios ``{"value": ..., "label": ...}``.
    - ``help_text``: texto adicional de ayuda para la interfaz.
    - ``depends_on``: ver ``DependsOn``.
    """

    id: str
    name: str
    type: str
    question: Optional[str] = None
    range: Optional[list[float]] = None
    options: list[Any] = field(default_factory=list)
    help_text: Optional[str] = None
    depends_on: Optional[DependsOn] = None

    def to_dict(self) -> dict:
        """Devuelve el atributo como diccionario listo para serializar a JSON.

        Omite los campos opcionales vacios para producir un JSON mas limpio.
        """
        datos = asdict(self)
        # Quitar campos opcionales no establecidos.
        if datos["question"] is None:
            del datos["question"]
        if datos["range"] is None:
            del datos["range"]
        if not datos["options"]:
            del datos["options"]
        if datos["help_text"] is None:
            del datos["help_text"]
        if datos["depends_on"] is None:
            del datos["depends_on"]
        return datos

    @classmethod
    def from_dict(cls, datos: dict) -> "Attribute":
        """Construye un ``Attribute`` desde un diccionario (p.ej. un JSON ya cargado)."""
        depends_on_datos = datos.get("depends_on")
        depends_on = DependsOn(**depends_on_datos) if depends_on_datos else None
        return cls(
            id=datos["id"],
            name=datos["name"],
            type=datos["type"],
            question=datos.get("question"),
            range=datos.get("range"),
            options=datos.get("options", []),
            help_text=datos.get("help_text"),
            depends_on=depends_on,
        )


class QuestionEditor:
    """Editor de atributos y preguntas del conocimiento del dominio.

    Mantiene los atributos en memoria y los serializa/deserializa a la seccion
    ``attributes`` de ``conocimiento_dominio.json``.

    Uso tipico::

        editor = QuestionEditor()
        editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                       type="numeric", question="Promedio?",
                                       range=[0.0, 3.0]))
        editor.save_to_json("conocimiento_dominio.json")
    """

    def __init__(self) -> None:
        # Diccionario de ``attribute_id -> Attribute``. Se mantiene un ``dict``
        # para preservar el orden de insercion (es el orden en que el Grupo 10
        # presentara las preguntas al usuario).
        self._attributes: dict[str, Attribute] = {}

    # --- Operaciones basicas (ya funcionan en el stub) ---

    def add_attribute(self, attr: Attribute) -> None:
        """Agrega un atributo nuevo.

        Levanta ``AttributeExistsError`` si ya existe un atributo con ese id.
        """
        if attr.id in self._attributes:
            raise AttributeExistsError(f"El atributo '{attr.id}' ya existe.")
        self._attributes[attr.id] = attr

    def edit_attribute(self, attribute_id: str, **changes: Any) -> None:
        """Modifica campos de un atributo existente.

        Levanta ``AttributeNotFoundError`` si no existe. Los ``changes`` son
        nombres de campo de ``Attribute`` y sus nuevos valores.
        """
        attr = self.get_attribute(attribute_id)
        for campo, valor in changes.items():
            if not hasattr(attr, campo):
                raise AttributeError(f"'Attribute' no tiene el campo '{campo}'.")
            setattr(attr, campo, valor)

    def delete_attribute(self, attribute_id: str) -> None:
        """Elimina un atributo.

        Levanta ``AttributeNotFoundError`` si no existe. No verifica si otras
        reglas o preguntas condicionales lo referencian (eso lo hara
        ``validate``).
        """
        if attribute_id not in self._attributes:
            raise AttributeNotFoundError(f"El atributo '{attribute_id}' no existe.")
        del self._attributes[attribute_id]

    def get_attribute(self, attribute_id: str) -> Attribute:
        """Devuelve el atributo con ese id.

        Levanta ``AttributeNotFoundError`` si no existe.
        """
        if attribute_id not in self._attributes:
            raise AttributeNotFoundError(f"El atributo '{attribute_id}' no existe.")
        return self._attributes[attribute_id]

    def list_attributes(self) -> list[Attribute]:
        """Devuelve todos los atributos en el orden en que se agregaron."""
        return list(self._attributes.values())

    # --- Operaciones pendientes (Sprint 1) ---

    def validate(self) -> dict:
        """Verifica la coherencia interna de la base de atributos.

        Debe comprobar, como minimo:
        - Ids unicos (garantizado por el dict, pero verificable).
        - ``type`` dentro de ``TIPOS_VALIDOS``.
        - Si ``type == 'numeric'`` y ``range`` existe: dos numeros, minimo <= maximo.
        - Si ``type == 'categorical'``: ``options`` no vacia y sin duplicados.
        - Si existe ``depends_on``: el ``attribute_id`` referenciado existe y
          el ``operator`` esta en ``OPERADORES_VALIDOS``.

        Devuelve ``{"valido": bool, "errores": list[str]}``.

        TODO Integrante B (Sprint 1).
        """
        raise NotImplementedError("validate() se implementa en Sprint 1 (Integrante B).")

    def save_to_json(self, path: str) -> None:
        """Escribe la seccion ``attributes`` del contrato en ``path``.

        Debe producir un JSON que respete el contrato acordado por la clase y
        que pase la validacion de ``SchemaManager`` (Grupo 4). Si el archivo
        ya existe y contiene otras secciones (``meta``, ``rules``), debe
        preservarlas y reemplazar solo ``attributes``.

        TODO Integrante A (Sprint 1).
        """
        raise NotImplementedError("save_to_json() se implementa en Sprint 1 (Integrante A).")

    def load_from_json(self, path: str) -> None:
        """Carga la seccion ``attributes`` desde ``path``.

        Sobrescribe el estado actual del editor con los atributos del archivo.

        TODO Integrante A (Sprint 1).
        """
        raise NotImplementedError("load_from_json() se implementa en Sprint 1 (Integrante A).")
