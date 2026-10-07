# Proguard rules for EMS Edge Android

# Chaquopy rules
-keep class com.chaquo.python.** { *; }

# Paho MQTT rules
-keep class org.eclipse.paho.client.mqttv3.** { *; }

# Gson rules
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.ems.edge.data.** { *; }
