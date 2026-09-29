import { API_URL } from "@/src/api";

import { storage } from "@/src/utils/storage";

import * as DocumentPicker from "expo-document-picker";

import * as ImagePicker from "expo-image-picker";

import { useState } from "react";

import {

  ActivityIndicator,
  Alert,

  Modal,

  Pressable,

  ScrollView,

  StyleSheet,

  Text,

  TextInput,

  View,

} from "react-native";

import { Ionicons } from "@expo/vector-icons";



type Step = "upload" | "prescription" | "symptoms" | "analysis";





export function PrescriptionFlow({

  visible,

  onClose,

}: {

  visible: boolean;

  onClose: () => void;

}) {

  const [step, setStep] = useState<Step>("upload");

  const [fileName, setFileName] = useState("");

  const [symptoms, setSymptoms] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [finalAnalysis, setFinalAnalysis] = useState<any>(null);
  const [detectedSymptoms, setDetectedSymptoms] = useState<
    { name: string; duration?: string }[]
  >([]);

  const quickSymptoms = [

    "Fever",

    "Headache",

    "Cough",

    "Sore throat",

    "Fatigue",

    "Nausea",

    "Pain",

    "Cold",

    "Dizziness",

  ];



  const reset = () => {

    setStep("upload");

    setFileName("");

    setSymptoms("");
    setAnalysisResult(null);
    setAnalyzing(false);

    setSelectedSymptoms([]);
    setDetectedSymptoms([]);
    setFinalAnalysis(null);

  };



  const close = () => {

    reset();

    onClose();

  };



  const chooseImage = async () => {
    const permission =
      await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert(
        "Permission required",
        "Please allow photo library access to choose a prescription image."
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: false,
      quality: 0.9,
    });

    if (result.canceled || !result.assets?.[0]) {
      return;
    }

    const asset = result.assets[0];
    const name =
      asset.fileName ||
      asset.uri.split("/").pop() ||
      "prescription-image.jpg";

    setFileName(name);
    setAnalyzing(true);

    try {
      const token = await storage.secureGet("justlocal_token", null);

      if (!token) {
        throw new Error("Your session has expired. Please sign in again.");
      }

      const formData = new FormData();

      if (typeof window !== "undefined") {
        // Web / Chrome
        const blobResponse = await fetch(asset.uri);
        const blob = await blobResponse.blob();

        formData.append(
          "file",
          blob,
          name || "prescription.jpg"
        );
      } else {
        // Android / iOS
        formData.append(
          "file",
          {
            uri: asset.uri,
            name: name || "prescription.jpg",
            type: asset.mimeType || "image/jpeg",
          } as any
        );
      }

      const response = await fetch(
        `${API_URL}/api/prescriptions/analyze`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${String(token)}`,
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail || "Prescription analysis failed. Please try again."
        );
      }

      console.log("Prescription analysis result:", data);
      setAnalysisResult(data);
      setStep("prescription");
    } catch (error) {
      Alert.alert(
        "Analysis failed",
        error instanceof Error
          ? error.message
          : "Unable to analyze the prescription."
      );
    } finally {
      setAnalyzing(false);
    }
  };
  const choosePdf = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        copyToCacheDirectory: true,
        multiple: false,
      });

      if (result.canceled || !result.assets?.length) {
        return;
      }

      const asset = result.assets[0];

      setFileName(asset.name || "prescription.pdf");

      Alert.alert(
        "PDF selected",
        "PDF selection is working. PDF analysis will be connected next."
      );
    } catch (error) {
      console.error("PDF picker error:", error);

      Alert.alert(
        "PDF upload",
        "Unable to open the PDF picker."
      );
    }
  };


  const toggleSymptom = (symptom: string) => {

    setSelectedSymptoms((current) =>

      current.includes(symptom)

        ? current.filter((item) => item !== symptom)

        : [...current, symptom]

    );

  };


  const goToSymptoms = () => {
    const rawSymptoms = Array.isArray(analysisResult?.symptoms)
      ? analysisResult.symptoms
      : [];

    const detected = rawSymptoms
      .filter((item: any) => item?.name && item.present !== false)
      .map((item: any) => ({
        name: String(item.name).trim(),
        duration: item.duration
          ? String(item.duration).trim()
          : undefined,
      }));

    console.log("Detected symptoms for UI:", detected);

    setDetectedSymptoms(detected);

    setSymptoms(
      detected
        .map((item) =>
          item.duration
            ? `${item.name} (${item.duration})`
            : item.name
        )
        .join("\n")
    );

    setSelectedSymptoms([]);
    setStep("symptoms");
  };
  const continueToAnalysis = async () => {
    if (!symptoms.trim() && selectedSymptoms.length === 0) {
      Alert.alert(
        "Add symptoms",
        "Please enter at least one symptom or select one from the suggestions."
      );
      return;
    }

    setAnalyzing(true);
    setStep("analysis");

    try {
      const token = await storage.secureGet("justlocal_token", null);

      if (!token) {
        throw new Error("Your session has expired. Please sign in again.");
      }

      // Build symptoms from the prescription-detected symptoms
      // and any additional symptoms selected by the patient.
      const detected = Array.isArray(detectedSymptoms)
        ? detectedSymptoms
        : [];

      const detectedNames = detected.map((item) =>
        String(item.name).trim().toLowerCase()
      );

      const additionalSymptoms = selectedSymptoms
        .filter(
          (item) =>
            !detectedNames.includes(String(item).trim().toLowerCase())
        )
        .map((item) => ({
          name: String(item).trim(),
          present: true,
        }));

      const allSymptoms = [
        ...detected.map((item) => ({
          name: item.name,
          duration: item.duration,
          present: true,
        })),
        ...additionalSymptoms,
      ];

      const medicines = Array.isArray(analysisResult?.medicines)
        ? analysisResult.medicines
        : [];

      console.log("Sending AI analysis request:", {
        medicines,
        symptoms: allSymptoms,
      });

      const response = await fetch(
        `${API_URL}/api/prescriptions/analyze-consistency`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${String(token)}`,
          },
          body: JSON.stringify({
            medicines,
            symptoms: allSymptoms,
          }),
        }
      );

      const data = await response.json();

      console.log("AI analysis response:", data);

      if (!response.ok) {
        throw new Error(
          data?.detail || "AI analysis failed. Please try again."
        );
      }

      setFinalAnalysis(data);
    } catch (error) {
      console.error("AI analysis error:", error);

      setFinalAnalysis(null);

      Alert.alert(
        "AI Analysis",
        error instanceof Error
          ? error.message
          : "Unable to complete AI analysis."
      );
    } finally {
      setAnalyzing(false);
    }
  };



  const renderHeader = (title: string, subtitle?: string) => (

    <View style={styles.header}>

      <Pressable onPress={close} style={styles.closeButton}>

        <Ionicons name="close" size={22} color="#20242A" />

      </Pressable>



      <View style={styles.headerText}>

        <Text style={styles.headerTitle}>{title}</Text>

        {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}

      </View>



      <View style={styles.headerSpacer} />

    </View>

  );



  const renderStepIndicator = () => {

    const steps: Step[] = ["upload", "prescription", "symptoms", "analysis"];

    const currentIndex = steps.indexOf(step);



    return (

      <View style={styles.stepRow}>

        {steps.map((item, index) => (

          <View key={item} style={styles.stepItem}>

            <View

              style={[

                styles.stepCircle,

                index <= currentIndex && styles.stepCircleActive,

              ]}

            >

              {index < currentIndex ? (

                <Ionicons name="checkmark" size={14} color="#FFFFFF" />

              ) : (

                <Text

                  style={[

                    styles.stepNumber,

                    index <= currentIndex && styles.stepNumberActive,

                  ]}

                >

                  {index + 1}

                </Text>

              )}

            </View>



            {index < steps.length - 1 ? (

              <View

                style={[

                  styles.stepLine,

                  index < currentIndex && styles.stepLineActive,

                ]}

              />

            ) : null}

          </View>

        ))}

      </View>

    );

  };



  const renderUpload = () => (

    <>

      {renderHeader(

        "Upload Prescription",

        "Start by uploading your prescription"

      )}



      {renderStepIndicator()}



      <View style={styles.intro}>

        <View style={styles.largeIcon}>

          <Ionicons name="document-text-outline" size={34} color="#3F8F72" />

        </View>



        <Text style={styles.title}>Upload Prescription</Text>



        <Text style={styles.description}>

          Upload a clear prescription image or PDF so the system can extract

          the medicines and dosage information.

        </Text>

      </View>



      <Pressable

        style={({ pressed }) => [

          styles.uploadOption,

          pressed && styles.pressed,

        ]}

        onPress={chooseImage}
        disabled={analyzing}

      >

        <View style={styles.optionIcon}>

          <Ionicons name="image-outline" size={24} color="#3F8F72" />

        </View>



        <View style={styles.optionContent}>

          {analyzing ? (
            <>
              <View style={{ flexDirection: "row", alignItems: "center" }}>
                <ActivityIndicator color="#3F8F72" size="small" />
                <Text style={[styles.optionTitle, { marginLeft: 8 }]}>
                  Analyzing prescription...
                </Text>
              </View>
              <Text style={styles.optionDescription}>
                Extracting medicines and prescription details
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.optionTitle}>Choose Image</Text>
              <Text style={styles.optionDescription}>
                JPG or PNG prescription image
              </Text>
            </>
          )}

        </View>



        <Ionicons name="chevron-forward" size={20} color="#8A919A" />

      </Pressable>



      <Pressable

        style={({ pressed }) => [

          styles.uploadOption,

          pressed && styles.pressed,

        ]}

        onPress={choosePdf}

      >

        <View style={styles.optionIcon}>

          <Ionicons name="document-outline" size={24} color="#3F8F72" />

        </View>



        <View style={styles.optionContent}>

          <Text style={styles.optionTitle}>Upload PDF</Text>

          <Text style={styles.optionDescription}>

            Prescription PDF document

          </Text>

        </View>



        <Ionicons name="chevron-forward" size={20} color="#8A919A" />

      </Pressable>



      <View style={styles.disclaimer}>

        <Ionicons name="information-circle-outline" size={18} color="#6D737B" />

        <Text style={styles.disclaimerText}>

          This tool extracts information from your prescription and does not

          replace professional medical advice.

        </Text>

      </View>

    </>

  );



  const renderPrescription = () => (

    <>

      {renderHeader(

        "Prescription Analysis",

        "Review the information extracted from your prescription"

      )}



      {renderStepIndicator()}



      <View style={styles.fileCard}>

        <View style={styles.fileIcon}>

          <Ionicons name="document-text" size={24} color="#3F8F72" />

        </View>



        <View style={styles.fileInfo}>

          <Text style={styles.fileTitle} numberOfLines={1}>

            {fileName || "prescription.jpg"}

          </Text>

          <Text style={styles.fileSubtitle}>Prescription analyzed successfully</Text>

        </View>



        <Ionicons name="checkmark-circle" size={22} color="#3F8F72" />

      </View>



      <Text style={styles.sectionTitle}>Extracted Medicines</Text>

      {Array.isArray(analysisResult?.medicines) &&
        analysisResult.medicines.length > 0 ? (
        analysisResult.medicines.map((medicine: any, index: number) => (
          <View
            key={`${medicine.name || "medicine"}-${index}`}
            style={styles.medicineCard}
          >
            <View style={styles.medicineNumber}>
              <Text style={styles.medicineNumberText}>{index + 1}</Text>
            </View>

            <View style={styles.medicineInfo}>
              <Text style={styles.medicineName}>
                {medicine.name || "Medicine name not identified"}
              </Text>

              <Text style={styles.medicineDetails}>
                {[medicine.strength, medicine.frequency, medicine.dosage]
                  .filter(Boolean)
                  .join(" · ") || "Details not identified"}
              </Text>

              {medicine.duration ? (
                <Text style={styles.medicineDuration}>
                  Duration: {medicine.duration}
                </Text>
              ) : null}
            </View>

            <Ionicons
              name="checkmark-circle"
              size={21}
              color="#3F8F72"
            />
          </View>
        ))
      ) : (
        <View style={styles.emptyResultCard}>
          <Ionicons
            name="alert-circle-outline"
            size={24}
            color="#8A919A"
          />
          <Text style={styles.emptyResultText}>
            No medicines could be confidently extracted from this
            prescription. Please verify the original image.
          </Text>
        </View>
      )}

      <Pressable

        style={({ pressed }) => [

          styles.primaryButton,

          pressed && styles.pressed,

        ]}

        onPress={goToSymptoms}

      >

        <Text style={styles.primaryButtonText}>Confirm Prescription</Text>

        <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />

      </Pressable>



      <Text style={styles.bottomNote}>

        The extracted information is for review and should be verified against

        the original prescription.

      </Text>

    </>

  );



  const renderSymptoms = () => (

    <>

      {renderHeader(

        "Describe Your Symptoms",

        "Tell us what you are currently experiencing"

      )}



      {renderStepIndicator()}



      <Text style={styles.title}>What are you currently experiencing?</Text>



      <Text style={styles.description}>

        Describe your symptoms in your own words. You can also select common

        symptoms below.

      </Text>
      {detectedSymptoms.length > 0 && (
        <View style={styles.detectedSymptomsContainer}>
          <Text style={styles.sectionTitle}>
            Detected from prescription
          </Text>

          {detectedSymptoms.map((item, index) => (
            <View
              key={`${item.name}-${index}`}
              style={styles.detectedSymptomCard}
            >
              <View style={styles.detectedSymptomIcon}>
                <Ionicons
                  name="checkmark"
                  size={16}
                  color="#FFFFFF"
                />
              </View>

              <View style={styles.detectedSymptomInfo}>
                <Text style={styles.detectedSymptomName}>
                  {item.name}
                </Text>

                {item.duration ? (
                  <Text style={styles.detectedSymptomDuration}>
                    Duration: {item.duration}
                  </Text>
                ) : null}
              </View>
            </View>
          ))}
        </View>
      )}


      <TextInput

        value={symptoms}

        onChangeText={setSymptoms}

        placeholder="e.g. fever, sore throat, headache..."

        placeholderTextColor="#9298A0"

        multiline

        textAlignVertical="top"

        style={styles.symptomInput}

      />



      <Text style={styles.sectionTitle}>Quick symptoms</Text>



      <View style={styles.chipContainer}>

        {quickSymptoms.map((symptom) => {

          const selected = selectedSymptoms.includes(symptom);



          return (

            <Pressable

              key={symptom}

              onPress={() => toggleSymptom(symptom)}

              style={[

                styles.chip,

                selected && styles.chipSelected,

              ]}

            >

              {selected ? (

                <Ionicons

                  name="checkmark"

                  size={14}

                  color="#FFFFFF"

                  style={{ marginRight: 5 }}

                />

              ) : null}



              <Text

                style={[

                  styles.chipText,

                  selected && styles.chipTextSelected,

                ]}

              >

                {symptom}

              </Text>

            </Pressable>

          );

        })}

      </View>



      <Pressable

        style={({ pressed }) => [

          styles.primaryButton,

          pressed && styles.pressed,

        ]}

        onPress={continueToAnalysis}

      >

        <Text style={styles.primaryButtonText}>Continue to Analysis</Text>

        <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />

      </Pressable>



      <Text style={styles.bottomNote}>

        Symptom information is used for navigation and consistency analysis.

        It is not a diagnosis.

      </Text>

    </>

  );



  const renderAnalysis = () => {

    const symptomText =

      symptoms.trim() ||

      (selectedSymptoms.length

        ? selectedSymptoms.join(", ")

        : "No symptoms entered");



    return (

      <>

        {renderHeader(

          "AI Analysis",

          "Prescription and symptom analysis"

        )}



        {renderStepIndicator()}



        <View style={styles.analysisHero}>

          <View style={styles.analysisIcon}>

            <Ionicons name="sparkles-outline" size={30} color="#3F8F72" />

          </View>



          <Text style={styles.analysisTitle}>Analysis Summary</Text>



          <Text style={styles.analysisDescription}>

            The information below is based on the prescription and symptoms

            entered in this demo.

          </Text>

        </View>



        <View style={styles.summaryCard}>

          <Text style={styles.summaryLabel}>Prescription</Text>

          <Text style={styles.summaryValue}>

            {Array.isArray(analysisResult?.medicines)
              ? `${analysisResult.medicines.length} medicines identified`
              : "Medicine extraction result unavailable"}

          </Text>

        </View>



        <View style={styles.summaryCard}>

          <Text style={styles.summaryLabel}>Reported symptoms</Text>

          <Text style={styles.summaryValue}>{symptomText}</Text>

        </View>



        <View style={styles.consistencyCard}>
          <View style={styles.consistencyIcon}>
            <Ionicons
              name="information-circle-outline"
              size={22}
              color="#3F8F72"
            />
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.consistencyLabel}>
              Prescription & symptom analysis
            </Text>

            <Text style={styles.specialtyName}>
              {analyzing
                ? "Analyzing..."
                : finalAnalysis?.analysis?.specialty ||
                "Not determined yet"}
            </Text>

            <Text style={styles.specialtyDescription}>
              {finalAnalysis?.analysis?.specialty
                ? "Specialty identified from the reported symptoms for healthcare navigation."
                : "Specialty classification uses the prescription and reported symptoms."}
            </Text>
          </View>
        </View>

        <View style={styles.specialtyCard}>
          <Text style={styles.summaryLabel}>Relevant Specialty</Text>

          <View style={styles.specialtyRow}>
            <View style={styles.specialtyIcon}>
              <Ionicons
                name={
                  analyzing
                    ? "sync-outline"
                    : finalAnalysis?.analysis?.status === "Broadly consistent"
                      ? "checkmark-circle-outline"
                      : "information-circle-outline"
                }
                size={22}
                color="#3F8F72"
              />
            </View>

            <View>
              <Text style={styles.specialtyName}>
                Not determined yet
              </Text>
              <Text style={styles.specialtyDescription}>
                Specialty classification will use the prescription and
                reported symptoms.
              </Text>
            </View>
          </View>
        </View>

        <Pressable

          style={({ pressed }) => [

            styles.primaryButton,

            pressed && styles.pressed,

          ]}

          onPress={() =>

            Alert.alert(

              "Hospital Navigation",

              "The next step will connect this specialty to the Hospitals screen."

            )

          }

        >

          <Text style={styles.primaryButtonText}>Find Hospitals</Text>

          <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />

        </Pressable>



        <Text style={styles.bottomNote}>

          This analysis is for navigation assistance only and does not provide

          a medical diagnosis or treatment recommendation.

        </Text>

      </>

    );

  };



  return (

    <Modal

      visible={visible}

      animationType="slide"

      onRequestClose={close}

    >

      <View style={styles.container}>

        <ScrollView

          contentContainerStyle={styles.scrollContent}

          keyboardShouldPersistTaps="handled"

          showsVerticalScrollIndicator={false}

        >

          {step === "upload" && renderUpload()}

          {step === "prescription" && renderPrescription()}

          {step === "symptoms" && renderSymptoms()}

          {step === "analysis" && renderAnalysis()}

        </ScrollView>

      </View>

    </Modal>

  );

}



const styles = StyleSheet.create({

  container: {

    flex: 1,

    backgroundColor: "#FFFFFF",

  },



  scrollContent: {

    paddingHorizontal: 20,

    paddingTop: 18,

    paddingBottom: 40,

  },



  header: {

    flexDirection: "row",

    alignItems: "center",

    minHeight: 58,

    marginBottom: 10,

  },



  closeButton: {

    width: 42,

    height: 42,

    borderRadius: 21,

    backgroundColor: "#F2F4F3",

    alignItems: "center",

    justifyContent: "center",

  },



  headerText: {

    flex: 1,

    marginHorizontal: 12,

  },



  headerTitle: {

    color: "#20242A",

    fontSize: 20,

    fontWeight: "800",

  },



  headerSubtitle: {

    color: "#747B83",

    fontSize: 12,

    marginTop: 3,

  },



  headerSpacer: {

    width: 42,

  },



  stepRow: {

    flexDirection: "row",

    alignItems: "center",

    marginVertical: 18,

    paddingHorizontal: 8,

  },



  stepItem: {

    flex: 1,

    flexDirection: "row",

    alignItems: "center",

  },



  stepCircle: {

    width: 28,

    height: 28,

    borderRadius: 14,

    backgroundColor: "#EEF0F0",

    alignItems: "center",

    justifyContent: "center",

  },



  stepCircleActive: {

    backgroundColor: "#3F8F72",

  },



  stepNumber: {

    color: "#858C93",

    fontSize: 12,

    fontWeight: "800",

  },



  stepNumberActive: {

    color: "#FFFFFF",

  },



  stepLine: {

    flex: 1,

    height: 2,

    backgroundColor: "#E4E7E7",

    marginHorizontal: 5,

  },



  stepLineActive: {

    backgroundColor: "#3F8F72",

  },



  intro: {

    alignItems: "center",

    marginTop: 10,

    marginBottom: 24,

  },



  largeIcon: {

    width: 78,

    height: 78,

    borderRadius: 24,

    backgroundColor: "#E7F3EE",

    alignItems: "center",

    justifyContent: "center",

    marginBottom: 16,

  },



  title: {

    color: "#20242A",

    fontSize: 23,

    fontWeight: "800",

    marginBottom: 8,

  },



  description: {

    color: "#747B83",

    fontSize: 14,

    lineHeight: 21,

    textAlign: "center",

    marginBottom: 22,

  },



  uploadOption: {

    minHeight: 76,

    borderRadius: 18,

    borderWidth: 1,

    borderColor: "#E1E5E3",

    backgroundColor: "#FAFBFA",

    flexDirection: "row",

    alignItems: "center",

    padding: 14,

    marginBottom: 12,

  },



  optionIcon: {

    width: 48,

    height: 48,

    borderRadius: 15,

    backgroundColor: "#E7F3EE",

    alignItems: "center",

    justifyContent: "center",

    marginRight: 13,

  },



  optionContent: {

    flex: 1,

  },



  optionTitle: {

    color: "#20242A",

    fontSize: 15,

    fontWeight: "800",

  },



  optionDescription: {

    color: "#7B8289",

    fontSize: 12,

    marginTop: 4,

  },



  pressed: {

    opacity: 0.72,

    transform: [{ scale: 0.99 }],

  },



  disclaimer: {

    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: "#F4F5F5",

    borderRadius: 15,

    padding: 13,

    marginTop: 12,

    gap: 8,

  },



  disclaimerText: {

    flex: 1,

    color: "#6D737B",

    fontSize: 11,

    lineHeight: 17,

  },



  fileCard: {

    flexDirection: "row",

    alignItems: "center",

    borderRadius: 17,

    backgroundColor: "#EAF4EF",

    padding: 14,

    marginBottom: 24,

  },



  fileIcon: {

    width: 45,

    height: 45,

    borderRadius: 14,

    backgroundColor: "#FFFFFF",

    alignItems: "center",

    justifyContent: "center",

    marginRight: 12,

  },



  fileInfo: {

    flex: 1,

  },



  fileTitle: {

    color: "#20242A",

    fontSize: 14,

    fontWeight: "800",

  },



  fileSubtitle: {

    color: "#6E7872",

    fontSize: 12,

    marginTop: 3,

  },



  sectionTitle: {

    color: "#20242A",

    fontSize: 17,

    fontWeight: "800",

    marginBottom: 12,

  },



  medicineCard: {

    flexDirection: "row",

    alignItems: "center",

    borderWidth: 1,

    borderColor: "#E3E6E4",

    borderRadius: 17,

    padding: 14,

    marginBottom: 10,

    backgroundColor: "#FFFFFF",

  },



  medicineNumber: {

    width: 34,

    height: 34,

    borderRadius: 17,

    backgroundColor: "#E7F3EE",

    alignItems: "center",

    justifyContent: "center",

    marginRight: 11,

  },



  medicineNumberText: {

    color: "#3F8F72",

    fontWeight: "800",

  },



  medicineInfo: {

    flex: 1,

  },



  medicineName: {

    color: "#20242A",

    fontSize: 15,

    fontWeight: "800",

  },



  medicineDetails: {

    color: "#555D65",

    fontSize: 12,

    marginTop: 4,

  },



  medicineDuration: {

    color: "#858C93",

    fontSize: 11,

    marginTop: 3,

  },



  primaryButton: {

    minHeight: 52,

    borderRadius: 17,

    backgroundColor: "#3F8F72",

    alignItems: "center",

    justifyContent: "center",

    flexDirection: "row",

    gap: 8,

    marginTop: 22,

  },



  primaryButtonText: {

    color: "#FFFFFF",

    fontSize: 14,

    fontWeight: "800",

  },



  bottomNote: {

    color: "#858C93",

    fontSize: 11,

    lineHeight: 17,

    textAlign: "center",

    marginTop: 13,

  },



  symptomInput: {

    minHeight: 145,

    borderRadius: 18,

    borderWidth: 1,

    borderColor: "#DDE2DF",

    backgroundColor: "#FAFBFA",

    color: "#20242A",

    fontSize: 14,

    lineHeight: 21,

    padding: 15,

    marginBottom: 24,

  },



  chipContainer: {

    flexDirection: "row",

    flexWrap: "wrap",

    gap: 9,

  },



  chip: {

    flexDirection: "row",

    alignItems: "center",

    borderRadius: 999,

    borderWidth: 1,

    borderColor: "#DCE1DE",

    backgroundColor: "#FFFFFF",

    paddingHorizontal: 13,

    paddingVertical: 9,

  },



  chipSelected: {

    backgroundColor: "#3F8F72",

    borderColor: "#3F8F72",

  },



  chipText: {

    color: "#555D65",

    fontSize: 12,

    fontWeight: "700",

  },



  chipTextSelected: {

    color: "#FFFFFF",

  },



  analysisHero: {

    alignItems: "center",

    backgroundColor: "#EAF4EF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 15,

  },



  analysisIcon: {

    width: 58,

    height: 58,

    borderRadius: 20,

    backgroundColor: "#FFFFFF",

    alignItems: "center",

    justifyContent: "center",

    marginBottom: 12,

  },



  analysisTitle: {

    color: "#20242A",

    fontSize: 21,

    fontWeight: "800",

  },



  analysisDescription: {

    color: "#657069",

    fontSize: 12,

    lineHeight: 18,

    textAlign: "center",

    marginTop: 6,

  },



  summaryCard: {

    borderWidth: 1,

    borderColor: "#E2E6E4",

    borderRadius: 17,

    padding: 15,

    marginBottom: 10,

  },



  summaryLabel: {

    color: "#858C93",

    fontSize: 11,

    fontWeight: "800",

    textTransform: "uppercase",

    letterSpacing: 0.5,

  },



  summaryValue: {

    color: "#20242A",

    fontSize: 14,

    fontWeight: "700",

    lineHeight: 20,

    marginTop: 6,

  },



  consistencyCard: {

    flexDirection: "row",

    backgroundColor: "#EAF4EF",

    borderRadius: 18,

    padding: 15,

    marginTop: 5,

  },



  consistencyIcon: {

    width: 40,

    height: 40,

    borderRadius: 20,

    backgroundColor: "#FFFFFF",

    alignItems: "center",

    justifyContent: "center",

    marginRight: 11,

  },



  consistencyLabel: {

    color: "#657069",

    fontSize: 11,

    fontWeight: "700",

  },



  consistencyResult: {

    color: "#2F735B",

    fontSize: 17,

    fontWeight: "900",

    marginTop: 4,

  },



  consistencyText: {

    color: "#657069",

    fontSize: 12,

    lineHeight: 18,

    marginTop: 6,

  },



  specialtyCard: {

    borderWidth: 1,

    borderColor: "#E2E6E4",

    borderRadius: 18,

    padding: 15,

    marginTop: 12,

  },



  specialtyRow: {

    flexDirection: "row",

    alignItems: "center",

    marginTop: 12,

  },



  specialtyIcon: {

    width: 46,

    height: 46,

    borderRadius: 15,

    backgroundColor: "#E7F3EE",

    alignItems: "center",

    justifyContent: "center",

    marginRight: 12,

  },



  specialtyName: {

    color: "#20242A",

    fontSize: 15,

    fontWeight: "800",

  },



  specialtyDescription: {

    color: "#858C93",

    fontSize: 11,

    marginTop: 4,

  },
  detectedSymptomsContainer: {
    marginBottom: 20,
  },

  detectedSymptomCard: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#DDE7E2",
    borderRadius: 15,
    backgroundColor: "#F7FBF9",
    padding: 12,
    marginBottom: 8,
  },

  detectedSymptomIcon: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#3F8F72",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 11,
  },

  detectedSymptomInfo: {
    flex: 1,
  },

  detectedSymptomName: {
    color: "#20242A",
    fontSize: 14,
    fontWeight: "800",
  },

  detectedSymptomDuration: {
    color: "#737B83",
    fontSize: 11,
    marginTop: 3,
  },
});
