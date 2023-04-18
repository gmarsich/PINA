"""Module for operators vectorize implementation"""
import torch

from pina.label_tensor import LabelTensor


def grad(output_, input_, components=None, d=None):
    """
        Perform gradient operation. The operator works for
        vectorial and scalar functions, with multiple input
        coordinates.

    :param output_: output of the PINN, i.e. function values.
    :type output_: LabelTensor
    :param input_: input of the PINN, i.e. function coordinates.
    :type input_: LabelTensor
    :param components: function components to apply the operator,
        defaults to None.
    :type components: list(str), optional
    :param d: coordinates of function components to be differentiated,
        defaults to None.
    :type d: list(str), optional
    """

    def grad_scalar_output(output_, input_, d):
        """
            Perform gradient operation for a scalar function.

        :param output_: output of the PINN, i.e. function values.
        :type output_: LabelTensor
        :param input_: input of the PINN, i.e. function coordinates.
        :type input_: LabelTensor
        :param d: coordinates of function components to be differentiated,
            defaults to None.
        :type d: list(str), optional
        :raises RuntimeError: a vectorial function is passed.
        :raises RuntimeError: missing derivative labels.
        :return: function gradients.
        :rtype: LabelTensor
        """

        if len(output_.labels) != 1:
            raise RuntimeError('only scalar function can be differentiated')
        if not all([di in input_.labels for di in d]):
            raise RuntimeError('derivative labels missing from input tensor')

        output_fieldname = output_.labels[0]
        gradients = torch.autograd.grad(
            output_,
            input_,
            grad_outputs=torch.ones(output_.size(), dtype=output_.dtype,
                                    device=output_.device),
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )[0]

        gradients.labels = input_.labels
        gradients = gradients.extract(d)
        gradients.labels = [f'd{output_fieldname}d{i}' for i in d]

        return gradients

    if not isinstance(input_, LabelTensor):
        raise TypeError

    if d is None:
        d = input_.labels

    if components is None:
        components = output_.labels

    if output_.shape[1] == 1:  # scalar output ################################

        if components != output_.labels:
            raise RuntimeError
        gradients = grad_scalar_output(output_, input_, d)

    elif output_.shape[1] >= 2:  # vector output ##############################

        for i, c in enumerate(components):
            c_output = output_.extract([c])
            if i == 0:
                gradients = grad_scalar_output(c_output, input_, d)
            else:
                gradients = gradients.append(
                    grad_scalar_output(c_output, input_, d))
    else:
        raise NotImplementedError

    return gradients


def div(output_, input_, components=None, d=None):
    """
        Perform divergence operation. The operator works for
        vectorial functions, with multiple input coordinates.

    :param output_: output of the PINN, i.e. function values.
    :type output_: LabelTensor
    :param input_: input of the PINN, i.e. function coordinates.
    :type input_: LabelTensor
    :param components: function components to apply the operator,
        defaults to None.
    :type components: list(str), optional
    :param d: coordinates of function components to be differentiated,
        defaults to None.
    :type d: list(str), optional
    :raises TypeError: div operator works only for LabelTensor.
    :raises ValueError: div operator works only for vector fields.
    :raises ValueError: div operator must derive all components with
        respect to all coordinates.
    :return: Function divergence.
    :rtype: LabelTensor
    """
    if not isinstance(input_, LabelTensor):
        raise TypeError

    if d is None:
        d = input_.labels

    if components is None:
        components = output_.labels

    if output_.shape[1] < 2 or len(components) < 2:
        raise ValueError('div supported only for vector fields')

    if len(components) != len(d):
        raise ValueError

    grad_output = grad(output_, input_, components, d)
    div = torch.zeros(input_.shape[0], 1, device=output_.device)
    labels = [None] * len(components)
    for i, (c, d) in enumerate(zip(components, d)):
        c_fields = f'd{c}d{d}'
        div[:, 0] += grad_output.extract(c_fields).sum(axis=1)
        labels[i] = c_fields

    div = div.as_subclass(LabelTensor)
    div.labels = ['+'.join(labels)]
    return div


def nabla(output_, input_, components=None, d=None, method='std'):
    """
        Perform nabla (laplace) operation. The operator works for
        vectorial and scalar functions, with multiple input
        coordinates.

    :param output_: output of the PINN, i.e. function values.
    :type output_: LabelTensor
    :param input_: input of the PINN, i.e. function coordinates.
    :type input_: LabelTensor
    :param components: function components to apply the operator,
        defaults to None.
    :type components: list(str), optional
    :param d: coordinates of function components to be differentiated,
        defaults to None.
    :type d: list(str), optional
    :param method: used method to calculate nabla, defaults to 'std'.
    :type method: str, optional including 'divgrad' where first gradient
        and later divergece operator are applied.
    :raises ValueError: for vectorial field derivative with respect to
        all coordinates must be performed.
    :raises NotImplementedError: 'divgrad' not implemented as method.
    :return: Function nabla.
    :rtype: LabelTensor
    """
    if d is None:
        d = input_.labels

    if components is None:
        components = output_.labels

    if len(components) != len(d) and len(components) != 1:
        raise ValueError

    if method == 'divgrad':
        raise NotImplementedError('divgrad not implemented as method')
        # TODO fix
        # grad_output = grad(output_, input_, components, d)
        # result = div(grad_output, input_, d=d)
    elif method == 'std':

        if len(components) == 1:
            grad_output = grad(output_, input_, components=components, d=d)
            result = torch.zeros(output_.shape[0], 1, device=output_.device)
            for i, label in enumerate(grad_output.labels):
                gg = grad(grad_output, input_, d=d, components=[label])
                result[:, 0] += gg[:, i]
            labels = [f'dd{components[0]}']

        else:
            result = torch.empty(input_.shape[0], len(components),
                                 device=output_.device)
            labels = [None] * len(components)
            for idx, (ci, di) in enumerate(zip(components, d)):

                if not isinstance(ci, list):
                    ci = [ci]
                if not isinstance(di, list):
                    di = [di]

                grad_output = grad(output_, input_, components=ci, d=di)
                result[:, idx] = grad(grad_output, input_, d=di).flatten()
                labels[idx] = f'dd{ci}dd{di}'

    result = result.as_subclass(LabelTensor)
    result.labels = labels
    return result


def advection(output_, input_, velocity_field, components=None, d=None):
    """
        Perform advection operation. The operator works for
        vectorial functions, with multiple input coordinates.

    :param output_: output of the PINN, i.e. function values.
    :type output_: LabelTensor
    :param input_: input of the PINN, i.e. function coordinates.
    :type input_: LabelTensor
    :param velocity_field: field used for multiplying the gradient.
    :type velocity_field: str
    :param components: function components to apply the operator,
        defaults to None.
    :type components: list(str), optional
    :param d: coordinates of function components to be differentiated,
        defaults to None.
    :type d: list(str), optional
    :return: Function advection.
    :rtype: LabelTensor
    """
    if d is None:
        d = input_.labels

    if components is None:
        components = output_.labels

    tmp = grad(output_, input_, components, d
               ).reshape(-1, len(components), len(d)).transpose(0, 1)

    tmp *= output_.extract(velocity_field)
    return tmp.sum(dim=2).T
