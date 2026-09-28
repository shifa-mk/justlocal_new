import { useState } from "react";
import { View } from "react-native";
import { PrescriptionFlow } from "../components/PrescriptionFlow";

export default function PrescriptionTest() {
  const [visible, setVisible] = useState(true);

  return (
    <View style={{ flex: 1 }}>
      <PrescriptionFlow
        visible={visible}
        onClose={() => setVisible(false)}
      />
    </View>
  );
}