# Description

This project provides a pure *Java* implementation of a *standalone* SmartDoor application. The implementation is heavily based on Axini's original, in-house Ruby implementation of the (standalone) SmartDoor SUT. With respect to the original Ruby version, however, only a single manufacturer is provided: the correct 'Axini' SmartDoor SUT. All other (buggy) implementations are not included in the application.

The software is distributed under the MIT license, see LICENSE.txt.

# Specification

The standalone SmartDoor application encapsulates a SmartDoor implementation, which can be accessed using a WebSocket connection: the SmartDoor application acts as a (non-secure) WebSocket server. Communication with the SmartDoor SUT is only with text messages. By default the SmartDoor application listens on `ws://127.0.0.1:3001`.

All messages and to (commands) and from (replies) the SmartDoor application are in UPPERCASE letters, e.g., `OPEN`, `CLOSE`, `CLOSED`, `INVALID_COMMAND` (the quotes `` are not part of the message). If a command has a parameter (`LOCK` and `UNLOCK`) it is separated by a double colon (`:``). For example: `LOCK:1234` and `UNLOCK:57291`.

The SmartDoor application supports all messages from the "SmartDoor IRS Version 2.0 (Sep 2020)" specification, but then in UPPERCASE. Furthermore, the SmartDoor application offers a `RESET` command to reset the SmartDoor completely (i.e., to the initial 'closed and unlocked' state). When the reset is finished, the SmartDoor application will send a `RESET_PERFORMED` message.


# Building the application - Maven

The Java application has been organized as a Maven application (https://maven.apache.org). The Java source files of the application reside in the following directory:
`./src/main/java/com/axini/smartdoor`.

The current implementation is based on Java 11, this can be updated in the following pom file property:

```xml
  <properties>
    <maven.compiler.source>YOUR JAVA VERSION HERE</maven.compiler.source>
    <maven.compiler.target>YOUR JAVA VERSION HERE</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
```

Make sure your maven version and Java version are in sync. The `$JAVA_HOME` env variable can be used to check this.

## Building executable jar *with* external dependencies

Maven's `pom.xml` defines all external dependencies and plugins to build a single jar archive including all external jars. The single jar with all dependencies can be built with:

```bash
mvn compile assembly:single
```

This will generate the following jar archive:

```bash
./target/standalone-smartdoor-<version>-jar-with-dependencies.jar
```

Where `<version>` is the version as specified in `pom.xml`. It is possible to rename the jar archive, of course.

The SmartDoor application can now be started with:

```bash
java -jar standalone-smartdoor-<version>-jar-with-dependencies.jar [<host> <port>]
```

A convenience script is provided as well:

```bash
./smartdoor
```

## Building executable jar without external libraries

It is also possible to build a jar archive with only the classes of the SmartDoor application:
```
$ mvn package
```
When executing the (small) generated jar, one now needs to specify the jar files of the external libraries.

## Cleaning up

After generating the Java classes and the jar file the repository can be cleaned up with (after copying the `.jar` file to safe place):

```bash
mvn clean
```

This will remove the `./target` directory, containing the compiled classes and jar files.

# External libraries

Maven's `pom.xml` specifies the two external dependencies of the SmartDoor application. When compiling the application with Maven, these dependencies are automatically downloaded from the Maven Central Repository: https://search.maven.org.

## Java-Websocket
https://github.com/TooTallNate/Java-WebSocket

## Simple Logging Facade For Java (SLF4J)
https://www.slf4j.org/

The file `./main/resources/simplelogger.properties` contains the (formatting) settings of the logger. This file is automatically copied to the resulting `jar` file of the SmartDoor application.

# Usage

By default, the SmartDoor application starts a WebSocket server at address `ws://127.0.0.1:3001`. This can be changed on the command-line, by specifying both the hostname and the port, for example:

```bash
java -jar standalone-smartdoor-<version>-jar-with-dependencies.jar localhost 1234
```

# Current limitations

- Documentation is lacking. No javadoc comments for methods.
- Error handling should be improved upon.
- (Unit) tests are missing. The SUT has been tested with AMP, though. ;-)
