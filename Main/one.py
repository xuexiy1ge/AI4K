'''输入540p --> 反卷积 --> 4K    和目标4K求差值'''

#先用花瓣图片做测试
import glob
from scipy import misc
import numpy as np
from keras.models import Sequential
from keras.layers import Conv2D,Activation,MaxPool2D,Flatten,Dense,BatchNormalization,Reshape,UpSampling2D
from keras import optimizers
from keras.callbacks import Callback
import matplotlib.pyplot as plt

small_images_path = "E:/data/small_images/*"
big_images_path = "E:/data/images/*"
small_arr = []
big_arr = []
for small_image, big_image in zip( glob.glob(small_images_path), glob.glob(big_images_path) ):
    # print(big_image,small_image)
    if small_image.split('\\')[-1] == big_image.split('\\')[-1]: #为确保万一，判断下文件名是否相等
        small_arr.append(misc.imread(small_image))
        big_arr.append(misc.imread(big_image))
    else:
        print('not like',big_image,small_image)
small_arr = np.array(small_arr)
big_arr = np.array(big_arr)
print(small_arr.shape) #(3000, 16, 16, 3)
small_arr2 = small_arr.reshape(-1,16*16*3)
print(small_arr2.shape) #(3000, 768)
print(big_arr.shape)   #(3000, 64, 64, 3)



 # 定义生成器模型
def generator_model():
    model = Sequential()
    # model.add(Dense(input_dim=16*16*3, units=128 * 16 * 16))
    # # # model.add(BatchNormalization())  # 批标准化
    # # model.add(Activation("tanh"))
    # model.add(Reshape((16, 16, 128), input_shape=(128 * 16 * 16,)))  # 16, 16 像素

    model.add( UpSampling2D(size=(2, 2), input_shape=(16,16,3)) )  # 输出：32 x 32像素
    # model.add( UpSampling2D(size=(2, 2)))  # 输出：32 x 32像素
    model.add(Conv2D(128, (5, 5), padding="same"))
    model.add(Activation("tanh"))

    model.add(UpSampling2D(size=(2, 2)))  # 输出：64 x 64像素
    model.add(Conv2D(3, (5, 5), padding="same"))
    model.add(Activation("tanh"))
    return model

g = generator_model()
g_optimizer = optimizers.SGD(lr=0.0001,momentum=0.9)
g.compile(loss="mse", optimizer=g_optimizer)
# g.summary()

#记录损失历史
class LossHistory(Callback):
    def on_train_begin(self, logs={}):
        self.losses = []
    def on_epoch_end(self, epoch, logs={}):
        # if epoch % 10 == 0:
            self.losses.append(logs.get('loss'))
history = LossHistory()
# g.fit(small_arr2, big_arr,callbacks = [history],batch_size = 128, epochs = 20)
g.fit(small_arr, big_arr,callbacks = [history],batch_size = 128, epochs = 20)


print(len(history.losses),history.losses)# 打印输出损失值

fig = plt.figure(figsize=(10, 7))
plt.plot(np.arange(len(history.losses)) * 100, history.losses, 'o-')
plt.xlabel('epoch')
plt.ylabel('MSE')
plt.show()

# model.save_weights("./weight2.h5", True) #保存模型 仅限权重
# model.load_weights("./weight2.h5") #加载权重

# len = 3
# data = []
# for i in range(len*len):
#     data.append(misc.imread('file'))
# data = np.array(data)
#
# images = g.predict(data, verbose=1)
# # images = images * 255
# # images = images.reshape((-1,28, 28)).astype(np.uint8)
# f, axarr = plt.subplots(len, len, sharex=True, figsize=(15, 15))
# for i in range(len * len):
#     ax = axarr[i // len, i % len]
#     ax.axis('off')
#     ax.imshow(images[i])
#     ax.set_title(i)
# plt.show()
