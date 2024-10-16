using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using UnityEngine;
using System.Threading;
using System;
using System.Text;
using System.Diagnostics;
using System.IO;
using UnityEditor.UI;
using Unity.VisualScripting;

public class NetworkHandler : MonoBehaviour
{
    public Thread main_thread;
    public string connection_ip = "127.0.0.1";
    public int connection_port = 25001;

    private IPAddress local_address;
    private TcpListener listener;
    private TcpClient client;

    public bool connected;

    public bool running;

    public Process python_app_process;

    public Queue<string> message_queue;

    private void Start()
    {
        this.running = false;
        this.connected = false;
        this.message_queue = new Queue<string>();
        string top_directory = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath));

        this.client = new TcpClient();

        // Try to connect to the python server once just to see if it's
        // running.
        bool connect_success = this.TryConnect(loop: false);

        // If we could not connect, start the python server.
        if (!connect_success)
        {
            // Start the python app.
            this.python_app_process = new Process();

            // The python app's main file should be under /src/app.py.
            string app_script_path = Path.Join(top_directory, "\\src\\app.py");
            //main_script_path = Path.Join(top_directory, "\\src\\test.py");
            //string python_3_12_path = "C:\\Users\\zevsm\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";

            this.python_app_process.StartInfo.FileName = "python.exe";
            this.python_app_process.StartInfo.Arguments = $"{app_script_path}";
            this.python_app_process.StartInfo.WorkingDirectory = top_directory;
            this.python_app_process.Start();
        }
        //process = Process.Start(start_info);
        //process.WaitForExit();
        //Process.Start("IExplore.exe", "www.northwindtraders.com");
        ThreadStart thread_start = new ThreadStart(Run);
        this.main_thread = new Thread(thread_start);
        this.main_thread.Start();
    }

    private void OnApplicationQuit()
    {
        this.Stop();
    }

    public void Stop()
    {
        // Stop running and clean up connections.
        // Stop the listener after the next message it receives.
        this.running = false;

        // Shut down the python server.
        //this.python_app_process.Kill();
        //this.SendMessage_("stop");
        // Disconnect from the python server.
        this.SendMessage_("disconnect");
    }

    // Try to connect to the python server.
    // Returns True if successfully connected,
    // False otherwise.
    private bool TryConnect(bool loop)
    {
        // Connect to the python server.
        while (true)
        {
            try
            {
                this.client.Connect("127.0.0.1", 25001);
            }
            catch
            {
                print("Client connection failed.");
                if (loop)
                    continue;
            }

            if (this.client.Connected)
            {
                print("Client connected!");
                this.connected = true;
                break;
            }
            else
            {
                print("Client connection failed.");
                if (!loop)
                    break;
            }
        }//end while

        return this.connected;
    }

    private void Run()
    {
        this.running = true;

        // If we're not already connected, try to connect to the python server.
        if (!this.connected)
        {
            this.TryConnect(loop: true);
        }

        // Loop and listen for data from the server.
        Byte[] buffer = new Byte[this.client.ReceiveBufferSize];
        while (this.running)
        {
            try
            {
                NetworkStream stream = this.client.GetStream();
                //stream.ReadTimeout = 5000;
                // Receive data from host (the python app)
                // Get data in bytes from python.
                int bytes_read = stream.Read(buffer, 0, this.client.ReceiveBufferSize);
                if (bytes_read == 0)
                    continue;
                // Decode into string
                string data_received = Encoding.UTF8.GetString(buffer, 0, bytes_read);

                if (data_received != null
                    && data_received != "")
                {
                    print("Received data: " + data_received);
                    this.message_queue.Enqueue(data_received);
                }
            }
            catch (Exception e)
            {
                print($"Exception in NetworkHandler.Run: {e}");
            }
        }
    }
    
    public void SendMessage_(string message)
    {
        // The client should be connected now.
        if (this.connected == false)
            return;
        // Send a message to the server
        NetworkStream stream = this.client.GetStream();
        if (stream.CanWrite)
        {
            byte[] byte_message = Encoding.ASCII.GetBytes(message);
            print("Sending message: " + message);
            stream.Write(byte_message, 0, byte_message.Length);
        }
    }

    public string ReadMessage(bool clear_message)
    {
        // Try to read a message from the message buffer.
        // Returns null if there are no messages to read.
        if (this.message_queue.Count == 0)
            return null;
        // If clear_message is true, removes the message read.
        string message = this.message_queue.Peek();
        if (clear_message)
            this.message_queue.Dequeue();
        return message;
    }

    private void Update()
    {
        //Console.WriteLine();
    }

}// end class SensemakerListener