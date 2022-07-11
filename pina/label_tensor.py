""" Module for LabelTensor """
import torch


class LabelTensor(torch.Tensor):
    """Torch tensor with a label for any column."""

    @staticmethod
    def __new__(cls, x, labels, *args, **kwargs):
        return super().__new__(cls, x, *args, **kwargs)

    def __init__(self, x, labels):
        '''
        Construct a `LabelTensor` by passing a tensor and a list of column
        labels. Such labels uniquely identify the columns of the tensor,
        allowing for an easier manipulation.

        :param torch.Tensor x: the data tensor.
        :param labels: the labels of the columns.
        :type labels: str or iterable(str)

        :Example:
            >>> from pina import LabelTensor
            >>> tensor = LabelTensor(torch.rand((2000, 3)), ['a', 'b', 'c'])
            >>> tensor
            tensor([[6.7116e-02, 4.8892e-01, 8.9452e-01],
                [9.2392e-01, 8.2065e-01, 4.1986e-04],
                [8.9266e-01, 5.5446e-01, 6.3500e-01],
                ...,
                [5.8194e-01, 9.4268e-01, 4.1841e-01],
                [1.0246e-01, 9.5179e-01, 3.7043e-02],
                [9.6150e-01, 8.0656e-01, 8.3824e-01]])
            >>> tensor.extract('a')
            tensor([[0.0671],
                    [0.9239],
                    [0.8927],
                    ...,
                    [0.5819],
                    [0.1025],
                    [0.9615]])
            >>> tensor.extract(['a', 'b'])
            tensor([[0.0671, 0.4889],
                    [0.9239, 0.8207],
                    [0.8927, 0.5545],
                    ...,
                    [0.5819, 0.9427],
                    [0.1025, 0.9518],
                    [0.9615, 0.8066]])
            >>> tensor.extract(['b', 'a'])
            tensor([[0.4889, 0.0671],
                    [0.8207, 0.9239],
                    [0.5545, 0.8927],
                    ...,
                    [0.9427, 0.5819],
                    [0.9518, 0.1025],
                    [0.8066, 0.9615]])
        '''
        if x.ndim == 1:
            x = x.reshape(-1, 1)

        if isinstance(labels, str):
            labels = [labels]

        if len(labels) != x.shape[1]:
            raise ValueError(
                'the tensor has not the same number of columns of '
                'the passed labels.'
            )
        self.labels = labels

    def clone(self, *args, **kwargs):
        """
        Clone the LabelTensor. For more details, see
        :meth:`torch.Tensor.clone`.

        :return: a copy of the tensor
        :rtype: LabelTensor
        """
        return LabelTensor(super().clone(*args, **kwargs), self.labels)

    def to(self, *args, **kwargs):
        """
        Performs Tensor dtype and/or device conversion. For more details, see
        :meth:`torch.Tensor.to`.
        """
        tmp = super().to(*args, **kwargs)
        new = self.__class__.clone(self)
        new.data = tmp.data
        return new

    def extract(self, label_to_extract):
        """
        Extract the subset of the original tensor by returning all the columns
        corresponding to the passed `label_to_extract`.

        :param label_to_extract: the label(s) to extract.
        :type label_to_extract: str or iterable(str)
        :raises TypeError: labels are not str
        :raises ValueError: label to extract is not in the labels list
        """

        if isinstance(label_to_extract, str):
            label_to_extract = [label_to_extract]
        elif isinstance(label_to_extract, (tuple, list)):  # TODO
            pass
        else:
            raise TypeError(
                '`label_to_extract` should be a str, or a str iterator')

        try:
            indeces = [self.labels.index(f) for f in label_to_extract]
        except ValueError:
            raise ValueError('`label_to_extract` not in the labels list')

        new_data = self[:, indeces].float()
        new_labels = [self.labels[idx] for idx in indeces]
        extracted_tensor = LabelTensor(new_data, new_labels)

        return extracted_tensor

    def append(self, lt):
        """
        Return a copy of the merged tensors.

        :param LabelTensor lt: the tensor to merge.
        :return: the merged tensors
        :rtype: LabelTensor
        """
        if set(self.labels).intersection(lt.labels):
            raise RuntimeError('The tensors to merge have common labels')

        new_labels = self.labels + lt.labels
        new_tensor = torch.cat((self, lt), dim=1)
        return LabelTensor(new_tensor, new_labels)

    def __str__(self):
        s = f'labels({str(self.labels)})\n'
        s += super().__str__()
        return s