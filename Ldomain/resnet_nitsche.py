'''
sys.argv[1]:
'1' means r^{1/2}\sin(\theta/2)
'2' means \nm{x}{2}^5
beta = sys.argv[2]
'''
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers

class ResNet(tf.keras.Model):
    def __init__(self, layer, unit, activation):
        super(ResNet, self).__init__()
        self.layer = layer
        self.fc1 = layers.Dense(unit, activation = activation)
        self.resnetlist = []
        for _ in range(layer):
            self.resnetlist.append(layers.Dense(unit, activation = activation))
            self.resnetlist.append(layers.Dense(unit, activation = activation))
        self.fc2 = layers.Dense(1, activation = None)
        
    def call(self, x):
        x = self.fc1(x)
        for i in range(self.layer):
            S = self.resnetlist[2*i](x)
            S = self.resnetlist[2*i+1](x)
            x += S
        return tf.squeeze(self.fc2(x))
        
    def compute_output_shape(self, input_shape):
        shape = tf.TensorShape(input_shape).as_list()
        return tf.TensorShape(shape[0])
        
class resnet_nitsche:
    def __init__(self, dimension, layer, unit, activation):
        self.dimension = dimension
        self.layer = layer
        self.unit = unit
        self.batch = 129
        self.batch_d = self.batch // (4 * dimension) + 1
        self.net = ResNet(layer, unit, activation)
        self.x_d = tf.compat.v1.placeholder(tf.float64, (None, dimension))
        self.x_i = tf.compat.v1.placeholder(tf.float64, (None, dimension))
        output_d = self.net(self.x_d)
        output_i = self.net(self.x_i)
        beta = float(sys.argv[2])
        self.loss_b = 8 * tf.reduce_mean(beta / 2 * output_d ** 2 - output_d * self.diff_n(output_d, self.x_d) - self.g_d(self.x_d) * (beta * output_d - self.diff_n(output_d, self.x_d)))
        self.loss_i = 3 * tf.reduce_mean(self.norm2_grad(output_i, self.x_i) / 2 - self.f(self.x_i) * output_i)
        self.loss = self.loss_b + self.loss_i
        self.opt = tf.compat.v1.train.AdamOptimizer(learning_rate = 0.001).minimize(self.loss)
        self.errl2 = self.l2(output_i - self.u(self.x_i), self.x_i) / self.l2(self.u(self.x_i), self.x_i)
        self.errh1 = self.h1(output_i - self.u(self.x_i), self.x_i) / self.h1(self.u(self.x_i), self.x_i)
        self.errh2 = self.h2(output_i - self.u(self.x_i), self.x_i) / self.h2(self.u(self.x_i), self.x_i)
        tf.compat.v1.summary.scalar('loss_b', self.loss_b)
        tf.compat.v1.summary.scalar('loss_i', self.loss_i)
        tf.compat.v1.summary.scalar('loss', self.loss)
        tf.compat.v1.summary.scalar('errl2', self.errl2)
        tf.compat.v1.summary.scalar('errh1', self.errh1)
        tf.compat.v1.summary.scalar('errh2', self.errh2)
        self.init = tf.compat.v1.global_variables_initializer()
        self.merged = tf.compat.v1.summary.merge_all()
        
    def u(self, x):
        if(sys.argv[1] == '1'):
            r = tf.sqrt(tf.reduce_sum(x ** 2, axis = 1))
            return tf.sqrt((r - x[:, 0]) / 2)
        elif(sys.argv[1] == '2'):
            return tf.reduce_sum(x ** 2, axis = 1) ** 2.5
        else:
            sys.exit("sys.argv[1] is error.")  
    
    def f(self, x):
        if(sys.argv[1] == '1'):
            return 0
        elif(sys.argv[1] == '2'):
            return -5 * (self.dimension + 3) * tf.reduce_sum(x ** 2, axis = 1) ** 1.5
        else:
            sys.exit("sys.argv[2] is error.")
        
    def g_d(self, x):
        return self.u(x)
        
    def norm2_grad(self, u, x):
        grad = tf.gradients(u, x)[0]
        return tf.reduce_sum(grad ** 2, axis = 1)

    def diff_n(self, u, x):
        grad = tf.gradients(u, x)[0]
        difflist = []
        for i in range(self.dimension):
            difflist.append(-grad[4*i*self.batch_d: (4*i+2)*self.batch_d, i])
            difflist.append(grad[(4*i+2)*self.batch_d: (4*i+4)*self.batch_d, i])
        return tf.concat(difflist, axis = 0)
        
    def l2(self, u, x):
        return tf.sqrt(3 * tf.reduce_mean(u ** 2))
        
    def h1(self, u, x):
        return tf.sqrt(3 * tf.reduce_mean(u ** 2 + self.norm2_grad(u, x)))
        
    def h2(self, u, x):
        ans = tf.reduce_mean(u ** 2 + self.norm2_grad(u, x))
        grad = tf.gradients(u, x)[0]
        for i in range(self.dimension):
            g = tf.gradients(grad[:, i], x)[0]
            ans += tf.reduce_mean(tf.reduce_sum(g ** 2, axis = 1))
        return tf.sqrt(3 * ans)
        
    def train(self, sess):
        x_d = np.random.rand(8*self.batch_d, self.dimension)
        for i in range(self.dimension):
            x_d[4*i*self.batch_d: (4*i+1)*self.batch_d, i] = -1.
            x_d[4*i*self.batch_d: (4*i+1)*self.batch_d, 1-i] -= 1.
            x_d[(4*i+1)*self.batch_d: (4*i+2)*self.batch_d, i] = -1.
            x_d[(4*i+2)*self.batch_d: (4*i+3)*self.batch_d, i] = 1.
            x_d[(4*i+2)*self.batch_d: (4*i+3)*self.batch_d, 1-i] -= 1.
            x_d[(4*i+3)*self.batch_d: (4*i+4)*self.batch_d, i] = 0.
        x_i = -np.random.rand(self.batch, self.dimension)
        x_i[: self.batch//3, 0] += 1.
        x_i[2*self.batch//3: , 1] += 1.
        _, summary = sess.run([self.opt, self.merged], feed_dict = {self.x_d: x_d, self.x_i: x_i})
        return summary
            
    def test(self, sess, batch_t):
        x_i = -np.random.rand(batch_t, self.dimension)
        x_i[: batch_t//3, 0] += 1.
        x_i[2*batch_t // 3: , 1] += 1.   
        return sess.run([self.errl2, self.errh1, self.errh2], feed_dict = {self.x_i: x_i})

tf.compat.v1.disable_eager_execution()
net = resnet_nitsche(2, 5, 10, "tanh") #dimension, layer, unit
with tf.Session() as sess:
    sess.run(net.init)
    train_writer = tf.compat.v1.summary.FileWriter('logs/rn', sess.graph)
    for i in range(50000):
        train_writer.add_summary(net.train(sess), i)
    errl2, errh1, errh2 = net.test(sess, 999999)
print("d = {}, l = {}, u = {}".format(net.dimension, net.layer, net.unit))
net.net.summary()
print(sys.argv)
print("{:e} & {:e} & {:e}\\\\".format(errl2, errh1, errh2))
