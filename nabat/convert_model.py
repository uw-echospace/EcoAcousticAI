import tensorflow as tf

# Path to the TensorFlow SavedModel directory (should be the folder, not `saved_model.pb`)
saved_model_path = "/Users/lawrie/Documents/EcoAcousticAI/NABAT/nabat-ml/prediction/tf-models/m-1"

# Load the model, but remove training-related components
loaded_model = tf.saved_model.load(saved_model_path)

# Extract the inference function (serving_default signature)
infer = loaded_model.signatures["serving_default"]

# Get input and output shapes
input_shapes = [tensor.shape.as_list() for tensor in infer.inputs]
output_shapes = [tensor.shape.as_list() for tensor in infer.outputs]

# Rebuild the model as a functional Keras model
inputs = [tf.keras.layers.Input(shape=shape[1:], dtype=tensor.dtype) for shape, tensor in zip(input_shapes, infer.inputs)]
outputs = infer(*inputs)

# If outputs is a dictionary (common in TensorFlow models), extract the tensor
if isinstance(outputs, dict):
    outputs = list(outputs.values())[0]

# Build a new Keras model
keras_model = tf.keras.Model(inputs=inputs, outputs=outputs)

# Save in Keras V3 format
new_model_path = saved_model_path + ".keras"
keras_model.save(new_model_path, save_format="keras")

print(f"✅ Model successfully converted and saved at: {new_model_path}")