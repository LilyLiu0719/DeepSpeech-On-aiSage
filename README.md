# DeepSpeech on aiSage 

## Step
1. clone deepspeech form https://github.com/mozilla/DeepSpeech.git
2. install tensorflow
3. download whl file and native_client.tar.xz form
 https://tools.taskcluster.net/index/project.deepspeech.deepspeech.native_client.v0.6.0-alpha.4/tflite
5. cp some required packages to new native_client
6. make -C native_client/python/ TFDIR=... bindings

## install pip3
https://blog.csdn.net/yuanlulu/article/details/87902106

`apt-get update`
`apt-get install python3-dev python3-pip`

## install tensorflow
github上已有人把arm64版本的tensorflow complie好了：
https://github.com/lhelontra/tensorflow-on-arm/releases
`pip3 install XXX.whl`
(take about 15 mins)

path: /home/aiSage/.local/lib/python3.5/site-packages/tensorflow

problem: tensorflow/lite does not have some required packages

## install Openjdk10
- 有人寫好的for aarch64的:
http://openjdk.linaro.org/relhome.htm?fbclid=IwAR2j44jF0SYBash9-DokMPA2pKtsvCaNlPfjfmNs94sy7DFswKcskUE1ZpU
- move to /opt and unzip
- add environment variable
`JAVA_HOME="/opt/"`
`PATH=$PATH:${JAVA_HOME}/bin`

## install bazel
**notice: please close all you browser while running program, or there will be memory error**
- Tutorial:
https://docs.bazel.build/versions/master/install-compile-source.html
https://www.cnblogs.com/svenwu/p/9546108.html

- download:
https://github.com/bazelbuild/bazel/releases?after=0.25.1
`sudo apt-get install build-essential openjdk-8-jdk python zip unzip`
version: 0.24.1(match tensorflow: 1.14.1)
`env BAZEL_JAVAC_OPTS="-J-Xms384m -J-Xmx1024m" EXTRA_BAZEL_ARGS="--host_javabase=@local_jdk//:jdk" bash ./compile.sh`

`env BAZEL_JAVAC_OPTS="-J-Xms384m -J-Xmx1024m" JAVA_TOOL_OPTS="-Xmx1500m" EXTRA_BAZEL_ARGS="--host_javabase=@local_jdk//:jdk" bash ./compile.sh
`

error: failed to create symbolic link '/tmp/bazel_zuMVyxQC/embedded_tools/tools/jdk/BUILD.pkg': File exists

try: use jdk10 instead of jdk8

### upgrade protobuf
- download latest version: https://github.com/protocolbuffers/protobuf/releases
- follow the steps from bazel/third_party/protobuf/README to modify BUILD file
- delete all PROTO_DEPS
- copy libprotobuf_java.jar and libprotobuf_java_util.jar from protobuf-3.6.1 to protobuf 3.9.0 

### symbolic link
- error message: 
ln: failed to create symbolic link: /tmp/XXX: file exists
- bazel/scripts/bootstrap/buildenv.sh:
-line 293, 310 add -sf after ln

### BUGS
- *ERROR: XXX Building XXX and running annotation processors (OptionProcessor, AutoAnnotationProcessor, AutoValueProcessor) failed: Worker process quit or closed its stdin stream when we tried to send a WorkRequest:*
==solution==: add parameter `JAVA_TOOL_OPTS="-Xmx1500m" `

- *ERROR: XX C++ compilation of rule XX failed (Exit 4): gcc failed: error executing command Target //src:bazel_nojdk failed to build*
*INFO: Elapsed time: 2259.911s, Critical Path: 960.87s*
*INFO: 1283 processes: 1239 local, 44 worker.*
==sloution==: add swap space 2G 
tutorial: https://linuxize.com/post/how-to-add-swap-space-on-debian-9/


- *ImportError: No module named 'deepspeech._impl'*


## Bazel build
`bazel build --workspace_status_command="bash native_client/bazel_workspace_status_cmd.sh" --config=monolithic --config=android --config=android_arm --cxxopt=-std=c++11 --copt=-D_GLIBCXX_USE_C99 --define=runtime=tflite //native_client:libdeepspeech.so > ~/file 2>&1`

## install swig
- toturial: https://www.dev2qa.com/how-to-install-swig-on-macos-linux-and-windows/

### Bugs
- *running build_ext
building 'deepspeech._impl' extension
swigging impl.i to impl_wrap.cpp
swig -python -c++ -keyword -builtin -o impl_wrap.cpp impl.i
impl.i:49: Error: Syntax error in input(1).
error: command 'swig' failed with exit status 1
Makefile:10: recipe for target 'bindings-build' failed*

## running 
make -C native_client/python/ bindings

`deepspeech --model models/output_graph.tflite --alphabet models/alphabet.txt --lm models/lm.binary --trie models/trie --audio sound/test0.wav`
### bugs
- *Data loss: Can't parse models/output_graph.tflite as binary proto
Traceback (most recent call last):
  File "/home/aiSage/tmp/deepspeech-venv/bin/deepspeech", line 10, in <module>
    sys.exit(main())
  File "/home/aiSage/tmp/deepspeech-venv/lib/python3.5/site-packages/deepspeech/client.py", line 91, in main
    ds = Model(args.model, N_FEATURES, N_CONTEXT, args.alphabet, BEAM_WIDTH)
  File "/home/aiSage/tmp/deepspeech-venv/lib/python3.5/site-packages/deepspeech/__init__.py", line 23, in __init__
    raise RuntimeError("CreateModel failed with error code {}".format(status))
RuntimeError: CreateModel failed with error code 12293*


## Memory Error
- swep
https://linuxize.com/post/how-to-add-swap-space-on-debian-9/

## Resource
https://www.tensorflow.org/lite/performance/gpu?fbclid=IwAR1fqcOsEdEy2L6Luu6VtIQz9jIAFznsKj8uKr8O639RaIP875wQCfUfuHM

bazel build --workspace_status_command="bash native_client/bazel_workspace_status_cmd.sh" --config=monolithic --config=rpi3-armv8 --config=rpi3-armv8_opt -c opt --copt=-O3 --copt=-fvisibility=hidden //native_client:libdeepspeech.so //native_client:generate_trie

export PATH=$PATH:/data/data/com.termux/files/usr/bin
