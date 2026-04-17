# fine_tune_restaurant.py

from tensorflow.keras.models import load_model, Model
from tensorflow.keras.layers import Dense
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# ---------------------------------------
# 1. Charger ancien modèle
# ---------------------------------------
base_model = load_model("Emotion_little_vgg.h5")

# ---------------------------------------
# 2. Freeze toutes les layers
# ---------------------------------------
for layer in base_model.layers:
    layer.trainable = False

# ---------------------------------------
# 3. Ouvrir dernières layers sauf output
# ---------------------------------------
for layer in base_model.layers[-8:-1]:
    layer.trainable = True

# ---------------------------------------
# 4. Remplacer output 7 classes -> 5 classes
# ---------------------------------------
x = base_model.layers[-2].output
output = Dense(5, activation='softmax', name='restaurant_output')(x)

model = Model(inputs=base_model.inputs, outputs=output)

# ---------------------------------------
# 5. Compiler
# ---------------------------------------
model.compile(
    optimizer=Adam(learning_rate=0.00001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# ---------------------------------------
# 6. Dataset path
# ---------------------------------------
dataset_path = "restaurant_dataset"

# ---------------------------------------
# 7. Data augmentation
# ---------------------------------------
train_datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2,
    rotation_range=10,
    zoom_range=0.1,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True
)

# ---------------------------------------
# 8. Train data
# ---------------------------------------
train_data = train_datagen.flow_from_directory(
    dataset_path,
    target_size=(48,48),
    color_mode="grayscale",
    batch_size=32,
    class_mode="categorical",
    subset="training"
)

# ---------------------------------------
# 9. Validation data
# ---------------------------------------
val_data = train_datagen.flow_from_directory(
    dataset_path,
    target_size=(48,48),
    color_mode="grayscale",
    batch_size=32,
    class_mode="categorical",
    subset="validation"
)

# ---------------------------------------
# 10. Callbacks
# ---------------------------------------
early_stop = EarlyStopping(
    monitor='val_loss',
    patience=4,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=2,
    verbose=1
)

# ---------------------------------------
# 11. Fine tuning
# ---------------------------------------
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=15,
    callbacks=[early_stop, reduce_lr]
)

# ---------------------------------------
# 12. Save nouveau modèle
# ---------------------------------------
model.save("Emotion_restaurant.h5")

print("Fine tuning terminé avec succès !")
print(train_data.class_indices)