import torch


def main():
    print(f"PyTorch version: {torch.__version__}")
    print(f"Built with CUDA support: {torch.version.cuda is not None}")

    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")

    if not cuda_available:
        print("PyTorch cannot access a CUDA GPU on this machine.")
        return

    device_index = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(device_index)
    sample_tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda")

    print(f"Using GPU {device_index}: {device_name}")
    print(f"Tensor device: {sample_tensor.device}")
    print(f"Tensor value: {sample_tensor}")


if __name__ == "__main__":
    main()
