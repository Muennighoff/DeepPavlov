# Copyright 2017 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from pathlib import Path
from typing import List, Union, Optional

import numpy as np
from overrides import overrides

from deeppavlov.core.common.errors import ConfigError
from deeppavlov.core.common.file import save_json, read_json
from deeppavlov.core.common.registry import register
from ...core.models.nn_model import NNModel

log = logging.getLogger(__name__)


@register('mem_classification_model')
class MemClassificationModel(NNModel):

    def __init__(self, n_classes: int, save_path: Optional[Union[str, Path]],
                 return_probas: bool = True, *args, **kwargs):
        super().__init__(save_path, *args, **kwargs)
        if n_classes == 0:
            raise ConfigError("Please, provide the number of classes setting")
        self.n_classes = n_classes
        self.opt = {
            "return_probas": return_probas,
        }
        self.save_path = save_path
        self.text2label = dict()
        self.classes = list()
        self.is_trained = False
        self.load()

    def __call__(self: "MemClassificationModel", texts: List[str], *args) -> Union[
        List[List[float]], List[int]]:
        """Infer on the given data.

        Args:
            texts: list of text samples

        Returns:
            for each sentence:
                vector of probabilities to belong with each class
                or list of classes sentence belongs with
        """
        outputs = np.zeros((len(texts), self.n_classes))
        for text_ix, text in enumerate(texts):
            label = self.text2label.get(text)
            if label is not None:
                outputs[text_ix][self.label2ix(label)] = 1.
        if self.opt["return_probas"]:
            return outputs.tolist()
        else:
            return np.argmax(outputs, axis=-1).tolist()

    def label2ix(self, label: str):
        if label not in self.classes:
            return -1
        return self.classes.index(label)

    def train_on_batch(self, texts: List[str],
                       labels: list) -> Union[float, List[float]]:
        """Train the model on the given batch.

        Args:
            texts: texts
            labels: list of classes

        Returns:
            metrics values on the given batch
        """
        if isinstance(labels, np.ndarray):
            labels = labels.tolist()
        if labels and isinstance(labels[0], np.ndarray):
            labels_ = []
            for lab in labels:
                label_ixes = np.where(lab)[0].tolist()
                if len(label_ixes) != 1:
                    log.warning("smth wrong with ohe")
                label_ix = label_ixes[0]
                labels_.append(label_ix)
            labels = labels_
        self.text2label.update(dict(zip(texts, labels)))
        self.classes = list(sorted(set(self.classes + labels)))
        # print(self.text2label)
        # print(self.classes)
        pseudo_loss = 0 if self.is_trained else 1
        self.is_trained = True
        self.save()
        return pseudo_loss

    @overrides
    def save(self, *args, **kwargs):
        # print("saving")
        save_json({"classes": self.classes,
                   "text2label": self.text2label},
                  self.save_path)

    @overrides
    def load(self, *args, **kwargs):
        # print("loading")
        try:
            loaded = read_json(self.save_path)
            self.classes = loaded["classes"]
            self.text2label = loaded["text2label"]
        except:
            log.info("nothing to load")